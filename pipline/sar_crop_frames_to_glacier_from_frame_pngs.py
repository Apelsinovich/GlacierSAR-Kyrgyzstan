#!/usr/bin/env python3
"""
Simple PNG Cropper - crop existing sar_frames PNG files to glacier area
No dB conversion, no brightness changes - just crop the good PNGs!
"""

import yaml
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def crop_png_frames():
    """Crop existing PNG frames from sar_frames folder"""
    
    config = load_config()
    glacier_areas = config['area']['glacier_areas']
    
    # Input and output directories
    frames_dir = Path("out/sar_frames")
    output_dir = Path("out/glacier_aoi_cropped_from_pngs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get PNG files from sar_frames
    png_files = list(frames_dir.glob("*.png"))
    
    if not png_files:
        print("❌ No PNG files found in out/sar_frames")
        return
    
    print(f"🖼️ CROPPING EXISTING PNG FRAMES")
    print(f"📂 Input: {frames_dir}")
    print(f"📁 Output: {output_dir}")
    print(f"🎯 Found {len(png_files)} PNG files")
    
    # We need to get coordinates from a TIF file to know the crop bounds
    tif_dir = Path(config['directories']['satellite_data'])
    sample_tif = list(tif_dir.glob("*_VV.tif"))[0]
    
    # Calculate pixel coordinates for cropping
    with rasterio.open(sample_tif) as src:
        
        for area in glacier_areas:
            min_lon, min_lat = area['min_lon'], area['min_lat']
            max_lon, max_lat = area['max_lon'], area['max_lat']
            
            # Convert to UTM bounds
            bbox_utm = transform_bounds("EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat)
            
            # Get window in pixels
            window = from_bounds(*bbox_utm, src.transform)
            
            # Convert to integer pixel coordinates
            col_off = int(window.col_off)
            row_off = int(window.row_off)
            width = int(window.width)
            height = int(window.height)
            
            print(f"\n🎯 Glacier area: {area['name']}")
            print(f"   📐 Crop box: x={col_off}, y={row_off}, w={width}, h={height}")
            
            crop_box = (col_off, row_off, col_off + width, row_off + height)
            
            successful = 0
            
            # Crop each PNG file
            for png_file in tqdm(png_files, desc="Cropping PNG frames"):
                
                try:
                    # Open PNG image
                    img = Image.open(png_file)
                    
                    # Crop to glacier area
                    cropped = img.crop(crop_box)
                    
                    # Save cropped image
                    output_file = output_dir / png_file.name
                    cropped.save(output_file)
                    
                    successful += 1
                    
                except Exception as e:
                    print(f"❌ Error with {png_file.name}: {e}")
            
            print(f"✅ Successfully cropped {successful}/{len(png_files)} PNG files")
            print(f"📁 Saved to: {output_dir}")
            
            # Show sample comparison
            if png_files:
                sample_file = png_files[0]
                sample_cropped = output_dir / sample_file.name
                
                if sample_cropped.exists():
                    # Load both images for comparison
                    original = Image.open(sample_file)
                    cropped = Image.open(sample_cropped)
                    
                    print(f"\n📊 SAMPLE COMPARISON:")
                    print(f"   Original: {original.size} pixels")
                    print(f"   Cropped:  {cropped.size} pixels")
                    print(f"   Reduction: {original.size[0]*original.size[1]//1000}K -> {cropped.size[0]*cropped.size[1]//1000}K pixels")

def main():
    crop_png_frames()

if __name__ == "__main__":
    main()