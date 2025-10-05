#!/usr/bin/env python3
"""
Crop Glacier Areas from SAR Frames with Coordinate Grid
Crops glacier areas from processed PNG frames and adds coordinate grid overlay
"""

import yaml
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageDraw, ImageFont
import rasterio
from rasterio.warp import transform_bounds
from rasterio.transform import rowcol
import re

def load_config():
    """Load configuration from YAML file"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def parse_date_from_name(filename):
    """Extract date from filename in YYYY-MM-DD format"""
    # Handle both PNG and TIF naming conventions
    m = re.search(r'(20\d{2}-\d{2}-\d{2})', filename)
    if m:
        return m.group(1)
    
    # Try OPERA format
    m = re.search(r'_(20\d{6})T', filename)
    if m:
        ymd = m.group(1)
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    
    return None

def get_tif_for_date(date_str, tif_dir):
    """Find the corresponding TIF file for a given date"""
    # Convert YYYY-MM-DD to YYYYMMDD for TIF matching
    clean_date = date_str.replace('-', '')
    
    # Look for TIF files with this date
    vv_files = list(tif_dir.glob(f"*{clean_date}*_VV.tif"))
    
    if vv_files:
        return vv_files[0]
    return None

def add_coordinate_grid_to_crop(img_array, tif_file, glacier_bounds, grid_spacing=0.02):
    """
    Add coordinate grid overlay to cropped glacier image
    
    img_array: cropped image array
    tif_file: original TIF file for coordinate reference
    glacier_bounds: [min_lon, min_lat, max_lon, max_lat] in WGS84
    grid_spacing: degrees between grid lines (0.005 = ~500m spacing for glacier scale)
    """
    
    # Convert grayscale to RGB for colored overlay
    if len(img_array.shape) == 2:
        img_rgb = np.stack([img_array, img_array, img_array], axis=-1)
    else:
        img_rgb = img_array.copy()
    
    img = Image.fromarray(img_rgb, mode='RGB')
    draw = ImageDraw.Draw(img)
    
    # Open TIF file for coordinate transformation
    try:
        with rasterio.open(tif_file) as src:
            min_lon, min_lat, max_lon, max_lat = glacier_bounds
            
            # Calculate grid lines
            # Longitude lines (vertical)
            lon_start = np.ceil(min_lon / grid_spacing) * grid_spacing
            lon_end = np.floor(max_lon / grid_spacing) * grid_spacing
            
            for lon in np.arange(lon_start, lon_end + grid_spacing, grid_spacing):
                if min_lon <= lon <= max_lon:
                    # Create points along the longitude line
                    lats = np.linspace(min_lat, max_lat, 20)
                    pixels = []
                    
                    for lat in lats:
                        try:
                            # Transform WGS84 to UTM (file CRS)
                            utm_bounds = transform_bounds("EPSG:4326", src.crs, lon, lat, lon, lat)
                            utm_x, utm_y = utm_bounds[0], utm_bounds[1]
                            
                            # Convert UTM to pixel coordinates in original image
                            row, col = rowcol(src.transform, utm_x, utm_y)
                            
                            # Convert original image pixel to cropped image pixel
                            # Calculate crop box in original image coordinates
                            crop_utm_bounds = transform_bounds("EPSG:4326", src.crs, 
                                                             min_lon, min_lat, max_lon, max_lat)
                            
                            # Get pixel coordinates of crop area
                            crop_row_min, crop_col_min = rowcol(src.transform, crop_utm_bounds[0], crop_utm_bounds[3])
                            crop_row_max, crop_col_max = rowcol(src.transform, crop_utm_bounds[2], crop_utm_bounds[1])
                            
                            # Calculate relative position in crop
                            if crop_row_min <= row <= crop_row_max and crop_col_min <= col <= crop_col_max:
                                crop_x = int((col - crop_col_min) * img.width / (crop_col_max - crop_col_min))
                                crop_y = int((row - crop_row_min) * img.height / (crop_row_max - crop_row_min))
                                
                                if 0 <= crop_x < img.width and 0 <= crop_y < img.height:
                                    pixels.append((crop_x, crop_y))
                        
                        except Exception:
                            continue
                    
                    # Draw line if we have enough points
                    if len(pixels) > 1:
                        draw.line(pixels, fill=(255, 255, 0), width=1)  # Yellow grid lines
                        
                        # Add longitude label
                        if pixels:
                            label_x, label_y = pixels[0]
                            draw.text((label_x + 2, max(2, label_y - 12)), 
                                    f"{lon:.3f}°", fill=(255, 255, 0))
            
            # Latitude lines (horizontal)
            lat_start = np.ceil(min_lat / grid_spacing) * grid_spacing
            lat_end = np.floor(max_lat / grid_spacing) * grid_spacing
            
            for lat in np.arange(lat_start, lat_end + grid_spacing, grid_spacing):
                if min_lat <= lat <= max_lat:
                    # Create points along the latitude line
                    lons = np.linspace(min_lon, max_lon, 20)
                    pixels = []
                    
                    for lon in lons:
                        try:
                            # Transform WGS84 to UTM (file CRS)
                            utm_bounds = transform_bounds("EPSG:4326", src.crs, lon, lat, lon, lat)
                            utm_x, utm_y = utm_bounds[0], utm_bounds[1]
                            
                            # Convert UTM to pixel coordinates in original image
                            row, col = rowcol(src.transform, utm_x, utm_y)
                            
                            # Convert original image pixel to cropped image pixel
                            # Calculate crop box in original image coordinates
                            crop_utm_bounds = transform_bounds("EPSG:4326", src.crs, 
                                                             min_lon, min_lat, max_lon, max_lat)
                            
                            # Get pixel coordinates of crop area
                            crop_row_min, crop_col_min = rowcol(src.transform, crop_utm_bounds[0], crop_utm_bounds[3])
                            crop_row_max, crop_col_max = rowcol(src.transform, crop_utm_bounds[2], crop_utm_bounds[1])
                            
                            # Calculate relative position in crop
                            if crop_row_min <= row <= crop_row_max and crop_col_min <= col <= crop_col_max:
                                crop_x = int((col - crop_col_min) * img.width / (crop_col_max - crop_col_min))
                                crop_y = int((row - crop_row_min) * img.height / (crop_row_max - crop_row_min))
                                
                                if 0 <= crop_x < img.width and 0 <= crop_y < img.height:
                                    pixels.append((crop_x, crop_y))
                        
                        except Exception:
                            continue
                    
                    # Draw line if we have enough points
                    if len(pixels) > 1:
                        draw.line(pixels, fill=(255, 255, 0), width=1)  # Yellow grid lines
                        
                        # Add latitude label
                        if pixels:
                            label_x, label_y = pixels[0]
                            draw.text((max(2, label_x - 35), label_y + 2), 
                                    f"{lat:.3f}°", fill=(255, 255, 0))
    
    except Exception as e:
        print(f"Warning: Could not add coordinate grid: {e}")
        # Return original image if grid addition fails
        pass
    
    return np.array(img)

def crop_png_frame_with_grid(png_file, tif_file, glacier_bounds, output_file):
    """Crop PNG frame to glacier area and add coordinate grid"""
    
    try:
        # Load PNG frame
        img = Image.open(png_file)
        img_array = np.array(img)
        
        # Get image dimensions
        height, width = img_array.shape[:2]
        
        # Open corresponding TIF for coordinate reference
        with rasterio.open(tif_file) as src:
            # Get file bounds in WGS84
            file_bounds_wgs84 = transform_bounds(
                src.crs, "EPSG:4326",
                src.bounds.left, src.bounds.bottom,
                src.bounds.right, src.bounds.top
            )
            
            min_file_lon, min_file_lat, max_file_lon, max_file_lat = file_bounds_wgs84
            min_glacier_lon, min_glacier_lat, max_glacier_lon, max_glacier_lat = glacier_bounds
            
            # Calculate crop coordinates as fractions of image size
            lon_fraction_left = (min_glacier_lon - min_file_lon) / (max_file_lon - min_file_lon)
            lon_fraction_right = (max_glacier_lon - min_file_lon) / (max_file_lon - min_file_lon)
            lat_fraction_bottom = (min_glacier_lat - min_file_lat) / (max_file_lat - min_file_lat)
            lat_fraction_top = (max_glacier_lat - min_file_lat) / (max_file_lat - min_file_lat)
            
            # Convert to pixel coordinates (PIL uses top-left origin)
            left = int(lon_fraction_left * width)
            right = int(lon_fraction_right * width)
            # Note: in images, top is 0, so we flip the lat fractions
            top = int((1 - lat_fraction_top) * height)
            bottom = int((1 - lat_fraction_bottom) * height)
            
            # Ensure coordinates are within bounds
            left = max(0, min(left, width))
            right = max(left, min(right, width))
            top = max(0, min(top, height))
            bottom = max(top, min(bottom, height))
            
            # Crop the image
            crop_box = (left, top, right, bottom)
            cropped_img = img.crop(crop_box)
            cropped_array = np.array(cropped_img)
            
            # Add coordinate grid
            cropped_with_grid = add_coordinate_grid_to_crop(cropped_array, tif_file, glacier_bounds)
            
            # Save result
            result_img = Image.fromarray(cropped_with_grid)
            result_img.save(output_file)
            
            crop_width = right - left
            crop_height = bottom - top
            
            return True, f"{crop_width}×{crop_height} pixels from {width}×{height}"
    
    except Exception as e:
        return False, str(e)

def crop_glacier_frames_with_grid():
    """Crop glacier areas from PNG frames and add coordinate grids"""
    
    config = load_config()
    
    # Get glacier bounds from config
    glacier_area = config['area']['glacier_areas'][0]  # Use first glacier area
    glacier_bounds = [
        glacier_area['min_lon'],
        glacier_area['min_lat'], 
        glacier_area['max_lon'],
        glacier_area['max_lat']
    ]
    glacier_name = config['area']['name']
    
    # Directories
    frame_dir = Path("out/sar_frames")
    tif_dir = Path(config['directories']['satellite_data'])
    output_dir = Path("out/glacier_cropped_from_frame_pngs_with_grid")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Glacier Frame Cropping with Coordinate Grid")
    print(f"Glacier: {glacier_name}")
    print(f"Bounds: {glacier_bounds} (WGS84)")
    print(f"Grid spacing: 0.02° (~2km)")
    print()
    
    # Find all PNG frames
    png_files = list(frame_dir.glob("*.png"))
    
    if not png_files:
        print(f"No PNG files found in {frame_dir}")
        print(f"Run 'python sar_generate_frames.py' first to create frames")
        return
    
    print(f"Found {len(png_files)} PNG frames")
    print("Cropping to glacier area and adding coordinate grid...")
    print()
    
    successful_crops = 0
    failed_crops = []
    
    for png_file in tqdm(sorted(png_files), desc="Cropping with grid"):
        
        # Parse date from filename
        date_str = parse_date_from_name(png_file.name)
        if not date_str:
            failed_crops.append((png_file.name, "Could not parse date"))
            continue
        
        # Find corresponding TIF file
        tif_file = get_tif_for_date(date_str, tif_dir)
        if not tif_file:
            failed_crops.append((png_file.name, f"No TIF file found for {date_str}"))
            continue
        
        # Output cropped file
        output_file = output_dir / f"{date_str}_glacier_with_grid.png"
        
        # Skip if already exists
        if output_file.exists():
            successful_crops += 1
            continue
        
        # Crop PNG frame with grid
        success, info = crop_png_frame_with_grid(png_file, tif_file, glacier_bounds, output_file)
        
        if success:
            successful_crops += 1
            
            # Show details for first few crops
            if successful_crops <= 3:
                print(f"  Created: {output_file.name} ({info})")
        else:
            failed_crops.append((png_file.name, info))
    
    print(f"\nResults:")
    print(f"Successfully cropped {successful_crops} frames with coordinate grid!")
    
    if failed_crops:
        print(f"Failed to process {len(failed_crops)} files")
        for filename, reason in failed_crops[:3]:
            print(f"  Failed: {filename}: {reason}")
        if len(failed_crops) > 3:
            print(f"  ... and {len(failed_crops) - 3} more failures")
    
    if successful_crops > 0:
        print(f"\nCropped frames saved in: {output_dir}")
        print(f"Each frame shows glacier area with coordinate grid overlay")
        print(f"Yellow grid lines show coordinate reference")
        
        print(f"\nCreate timelapse:")
        print(f"ffmpeg -framerate 6 -pattern_type glob -i '{output_dir}/*_glacier_with_grid.png' -c:v libx264 -pix_fmt yuv420p -crf 18 {glacier_name.lower().replace(' ', '_')}_glacier_grid_timelapse.mp4")
    
    return successful_crops

if __name__ == "__main__":
    crop_glacier_frames_with_grid()