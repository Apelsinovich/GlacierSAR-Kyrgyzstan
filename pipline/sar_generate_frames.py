#!/usr/bin/env python3
"""
PNG Frame Generator from VV GeoTIFF files
Processes downloaded VV.tif files and creates PNG frames with proper contrast
"""

import yaml
import numpy as np
import re
from pathlib import Path
from tqdm import tqdm

try:
    import rasterio
    from PIL import Image
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install rasterio Pillow")
    exit(1)

def load_config():
    """Load configuration from YAML file"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def linear_stretch_db(arr, lo, hi):
    """Apply linear stretch to dB values for visualization"""
    arr = np.clip((arr - lo) / (hi - lo), 0, 1)
    return (arr * 255).astype(np.uint8)

def parse_date_from_name(filename):
    """Extract date from OPERA filename in YYYY-MM-DD format"""
    # Look for pattern like 20200607T010505 in filename
    m = re.search(r'_(20\d{6})T', filename)
    if m:
        ymd = m.group(1)
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return None

def process_vv_tif_to_png(tif_file, output_dir, db_range):
    """Convert a single VV.tif file to PNG frame"""
    
    # Parse date from filename
    date_str = parse_date_from_name(tif_file.name)
    if not date_str:
        print(f"  Could not parse date from: {tif_file.name}")
        return False
    
    # Output PNG path
    png_file = output_dir / f"{date_str}.png"
    
    # Skip if already exists
    if png_file.exists():
        return True
    
    try:
        with rasterio.open(tif_file) as src:
            # Read VV data (first band)
            vv_data = src.read(1)
            
            # Handle no-data values
            if src.nodata is not None:
                vv_data = np.where(vv_data == src.nodata, np.nan, vv_data)
            
            # Convert to dB if not already (OPERA RTC products are in linear power scale)
            if np.nanmax(vv_data) > 10:  # Likely linear scale
                vv_data = 10 * np.log10(np.maximum(vv_data, 1e-10))
            
            # Replace NaN with minimum dB for display
            vv_data = np.where(np.isnan(vv_data), db_range[0], vv_data)
            
            # Apply your original dB stretch
            frame = linear_stretch_db(vv_data, db_range[0], db_range[1])
            
            # Create and save PNG
            img = Image.fromarray(frame, mode='L')
            img.save(png_file)
            
            return True
            
    except Exception as e:
        print(f"  Error processing {tif_file.name}: {e}")
        return False

def generate_frames():
    """Generate PNG frames from all VV.tif files"""
    
    config = load_config()
    
    # Directories
    tif_dir = Path(config['directories']['satellite_data'])
    frames_dir = Path(config['directories']['frames'])
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Processing parameters
    db_range = config['processing']['db_range']
    
    print(f"PNG Frame Generator")
    print(f"Input directory: {tif_dir}")
    print(f"Output directory: {frames_dir}")
    print(f"dB Range: {db_range} (glaciers appear darker)")
    print()
    
    # Find all VV.tif files
    vv_files = list(tif_dir.glob("*_VV.tif"))
    
    if not vv_files:
        print(f"No VV.tif files found in {tif_dir}")
        print("Run download_vv_tifs.py first!")
        return
    
    print(f"Found {len(vv_files)} VV.tif files")
    
    successful_frames = 0
    
    for tif_file in tqdm(sorted(vv_files), desc="Creating PNG frames"):
        if process_vv_tif_to_png(tif_file, frames_dir, db_range):
            successful_frames += 1
            
            # Show progress for first few
            if successful_frames <= 3:
                date_str = parse_date_from_name(tif_file.name)
                print(f"  Created: {date_str}.png")
    
    print(f"\nSuccessfully created {successful_frames} PNG frames!")
    print(f"Frames saved in: {frames_dir}")
    
    if successful_frames > 0:
        print(f"\nTo create video:")
        print(f"ffmpeg -framerate 6 -pattern_type glob -i '{frames_dir}/*.png' -c:v libx264 -pix_fmt yuv420p -crf 18 glacier_timelapse.mp4")

if __name__ == "__main__":
    generate_frames()