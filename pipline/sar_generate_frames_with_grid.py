#!/usr/bin/env python3
"""
Enhanced Frame Generator with Coordinate Mesh
Generates frames with coordinate grid overlay for easy reference
"""

import yaml
import numpy as np
from pathlib import Path
from tqdm import tqdm
import rasterio
from rasterio.warp import transform_bounds
from PIL import Image, ImageDraw, ImageFont
import re

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
    m = re.search(r'_(20\d{6})T', filename)
    if m:
        ymd = m.group(1)
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return None

def add_coordinate_mesh(img_array, src, grid_spacing=0.02, line_color=(255, 255, 0), text_color=(255, 255, 0)):
    """
    Add coordinate mesh overlay to SAR image
    
    grid_spacing: degrees between grid lines (0.02 = ~2km spacing)
    """
    
    # Convert grayscale to RGB for colored overlay
    if len(img_array.shape) == 2:
        img_rgb = np.stack([img_array, img_array, img_array], axis=-1)
    else:
        img_rgb = img_array.copy()
    
    img = Image.fromarray(img_rgb, mode='RGB')
    draw = ImageDraw.Draw(img)
    
    # Get file bounds in WGS84
    file_bounds_wgs84 = transform_bounds(
        src.crs, "EPSG:4326",
        src.bounds.left, src.bounds.bottom,
        src.bounds.right, src.bounds.top
    )
    
    min_lon, min_lat, max_lon, max_lat = file_bounds_wgs84
    
    # Calculate grid lines
    # Longitude lines (vertical)
    lon_start = np.floor(min_lon / grid_spacing) * grid_spacing
    lon_end = np.ceil(max_lon / grid_spacing) * grid_spacing
    
    for lon in np.arange(lon_start, lon_end + grid_spacing, grid_spacing):
        if min_lon <= lon <= max_lon:
            # Transform longitude line to pixel coordinates
            try:
                # Create points along the longitude line
                lats = np.linspace(min_lat, max_lat, 10)
                coords = [(lon, lat) for lat in lats]
                
                # Transform to UTM (file CRS)
                pixels = []
                for coord_lon, coord_lat in coords:
                    utm_bounds = transform_bounds("EPSG:4326", src.crs, coord_lon, coord_lat, coord_lon, coord_lat)
                    utm_x, utm_y = utm_bounds[0], utm_bounds[1]
                    
                    # Convert UTM to pixel
                    px, py = rasterio.transform.rowcol(src.transform, utm_x, utm_y)
                    py, px = px, py  # rowcol returns (row, col) = (y, x)
                    
                    if 0 <= px < src.width and 0 <= py < src.height:
                        pixels.append((px, py))
                
                # Draw line
                if len(pixels) > 1:
                    draw.line(pixels, fill=line_color, width=2)
                    
                    # Add longitude label at top
                    if pixels:
                        label_x, label_y = pixels[0]
                        draw.text((label_x + 3, max(5, label_y - 15)), f"{lon:.3f}°E", fill=text_color)
                        
            except Exception:
                continue
    
    # Latitude lines (horizontal)  
    lat_start = np.floor(min_lat / grid_spacing) * grid_spacing
    lat_end = np.ceil(max_lat / grid_spacing) * grid_spacing
    
    for lat in np.arange(lat_start, lat_end + grid_spacing, grid_spacing):
        if min_lat <= lat <= max_lat:
            # Transform latitude line to pixel coordinates
            try:
                # Create points along the latitude line
                lons = np.linspace(min_lon, max_lon, 10)
                coords = [(lon, lat) for lon in lons]
                
                # Transform to UTM (file CRS)
                pixels = []
                for coord_lon, coord_lat in coords:
                    utm_bounds = transform_bounds("EPSG:4326", src.crs, coord_lon, coord_lat, coord_lon, coord_lat)
                    utm_x, utm_y = utm_bounds[0], utm_bounds[1]
                    
                    # Convert UTM to pixel
                    px, py = rasterio.transform.rowcol(src.transform, utm_x, utm_y)
                    py, px = px, py  # rowcol returns (row, col) = (y, x)
                    
                    if 0 <= px < src.width and 0 <= py < src.height:
                        pixels.append((px, py))
                
                # Draw line
                if len(pixels) > 1:
                    draw.line(pixels, fill=line_color, width=2)
                    
                    # Add latitude label at left
                    if pixels:
                        label_x, label_y = pixels[0]
                        draw.text((max(5, label_x - 50), label_y + 3), f"{lat:.3f}°N", fill=text_color)
                        
            except Exception:
                continue
    
    return np.array(img)

def process_vv_tif_to_frame_with_mesh(tif_file, db_range, output_file, grid_spacing=0.02):
    """Process VV.tif to PNG frame with coordinate mesh overlay"""
    
    try:
        with rasterio.open(tif_file) as src:
            # Read full data
            vv_data = src.read(1)
            
            # Handle no-data values
            if src.nodata is not None:
                vv_data = np.where(vv_data == src.nodata, np.nan, vv_data)
            
            # Convert to dB if needed (OPERA RTC products are in linear power scale)
            valid_data = vv_data[~np.isnan(vv_data)]
            if len(valid_data) > 0 and np.max(valid_data) > 10:  # Likely linear scale
                vv_data = np.where(vv_data > 0, 10 * np.log10(vv_data), np.nan)
            
            # Replace NaN with minimum dB for display
            vv_data = np.where(np.isnan(vv_data), db_range[0], vv_data)
            
            # Apply linear stretch to 0-255 range
            frame = linear_stretch_db(vv_data, db_range[0], db_range[1])
            
            # Add coordinate mesh overlay
            frame_with_mesh = add_coordinate_mesh(frame, src, grid_spacing)
            
            # Create and save PNG
            img = Image.fromarray(frame_with_mesh, mode='RGB')
            img.save(output_file)
            
            return True, f"{frame.shape[1]}x{frame.shape[0]} pixels"
            
    except Exception as e:
        return False, str(e)

def generate_frames_with_mesh():
    """Generate SAR frames with coordinate mesh overlay"""
    
    config = load_config()
    
    # Get configuration
    db_range = config['processing']['db_range']
    glacier_name = config['area']['name']
    
    # Directories
    tif_dir = Path(config['directories']['satellite_data'])
    output_dir = Path("out/sar_frames_with_grid")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"SAR Frame Generator with Coordinate Mesh")
    print(f"Glacier: {glacier_name}")
    print(f"dB Range: {db_range}")
    print(f"Grid spacing: 0.02° (~2km)")
    print()
    
    # Find all VV.tif files
    vv_files = list(tif_dir.glob("*_VV.tif"))
    
    if not vv_files:
        print(f"No VV.tif files found in {tif_dir}")
        return
    
    print(f"Found {len(vv_files)} VV.tif files")
    print("Generating frames with coordinate mesh...")
    print()
    
    successful_frames = 0
    failed_frames = []
    
    for tif_file in tqdm(sorted(vv_files), desc="Creating frames with mesh"):
        
        # Parse date from filename
        date_str = parse_date_from_name(tif_file.name)
        if not date_str:
            continue
        
        # Output PNG file
        png_file = output_dir / f"{date_str}_with_mesh.png"
        
        # Skip if already exists
        if png_file.exists():
            successful_frames += 1
            continue
        
        # Process TIF to PNG with mesh
        success, info = process_vv_tif_to_frame_with_mesh(tif_file, db_range, png_file)
        
        if success:
            successful_frames += 1
            
            # Show details for first few frames
            if successful_frames <= 3:
                print(f"  Created: {png_file.name} ({info})")
        else:
            failed_frames.append((tif_file.name, info))
    
    print(f"\nResults:")
    print(f"Successfully created {successful_frames} frames with coordinate mesh!")
    
    if failed_frames:
        print(f"Failed to process {len(failed_frames)} files")
        for filename, reason in failed_frames[:3]:
            print(f"  Failed: {filename[:50]}...: {reason}")
        if len(failed_frames) > 3:
            print(f"  ... and {len(failed_frames) - 3} more failures")
    
    if successful_frames > 0:
        print(f"\nFrames saved in: {output_dir}")
        print(f"Each frame shows coordinate grid for reference")
        print(f"Glacier location: ~74.435°E, ~42.501°N (from your observation)")
        
        print(f"\nNext steps:")
        print(f"1. Update config.yaml with glacier coordinates: [74.43, 42.44, 74.45, 42.52]")
        print(f"2. Run PNG cropping: python sar_crop_frames_to_glacier_from_frame_pngs.py")
        print(f"   Or TIF cropping: python sar_crop_frames_to_glacier_from_satellite_data.py")
        print(f"3. Create timelapse from cropped frames")
        
        print(f"\nOr create timelapse from full frames with mesh:")
        print(f"ffmpeg -framerate 6 -pattern_type glob -i '{output_dir}/*_with_mesh.png' -c:v libx264 -pix_fmt yuv420p -crf 18 {glacier_name.lower().replace(' ', '_')}_full_mesh_timelapse.mp4")
    
    return successful_frames

if __name__ == "__main__":
    generate_frames_with_mesh()