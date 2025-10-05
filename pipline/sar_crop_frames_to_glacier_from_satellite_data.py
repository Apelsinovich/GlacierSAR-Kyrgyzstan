#!/usr/bin/env python3
"""
Clean Glacier Cropper
Crops frames to glacier area without mesh overlay
Uses glacier_area coordinates from config.yaml
"""

import yaml
import numpy as np
from pathlib import Path
from tqdm import tqdm
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
from PIL import Image
import re

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def parse_date_from_name(filename):
    m = re.search(r'_(20\d{6})T', filename)
    if m:
        ymd = m.group(1)
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return None

def adaptive_linear_stretch(arr, percentile_range=(10, 90)):
    valid_data = arr[~np.isnan(arr)]
    if len(valid_data) == 0:
        return (arr * 0).astype(np.uint8)
    
    # Use less aggressive stretch to avoid brightness
    low_val = np.percentile(valid_data, percentile_range[0])
    high_val = np.percentile(valid_data, percentile_range[1])
    
    if high_val - low_val < 0.1:
        low_val = np.min(valid_data)
        high_val = np.max(valid_data)
        if high_val - low_val < 0.1:
            high_val = low_val + 1.0
    
    stretched = np.clip((arr - low_val) / (high_val - low_val), 0, 1)
    return (stretched * 255).astype(np.uint8)

def crop_and_combine_areas(tif_file, glacier_areas, output_file):
    """Crop multiple coordinate boxes and combine into one image"""
    
    try:
        with rasterio.open(tif_file) as src:
            area_crops = []
            
            # Crop each area
            for area in glacier_areas:
                min_lon, min_lat = area['min_lon'], area['min_lat']
                max_lon, max_lat = area['max_lon'], area['max_lat']
                
                bbox_utm = transform_bounds("EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat)
                window = from_bounds(*bbox_utm, src.transform)
                
                if window.width <= 0 or window.height <= 0:
                    continue
                
                vv_data = src.read(1, window=window)
                if vv_data.size == 0:
                    continue
                
                if src.nodata is not None:
                    vv_data = np.where(vv_data == src.nodata, np.nan, vv_data)
                
                if not np.any(~np.isnan(vv_data)):
                    continue
                
                # Convert to dB if needed
                valid_data = vv_data[~np.isnan(vv_data)]
                if len(valid_data) > 0 and np.max(valid_data) > 10:
                    vv_data = np.where(vv_data > 0, 10 * np.log10(vv_data), np.nan)
                
                # Fill NaN and apply adaptive stretch
                min_valid = np.nanmin(vv_data)
                vv_data_filled = np.where(np.isnan(vv_data), min_valid - 10, vv_data)
                frame = adaptive_linear_stretch(vv_data_filled)
                
                area_crops.append((area['name'], frame))
            
            if not area_crops:
                return False
            
            # Combine areas into one image
            if len(area_crops) == 1:
                # Single area - just save it
                combined_frame = area_crops[0][1]
            else:
                # Multiple areas - arrange horizontally or vertically
                total_width = sum(crop[1].shape[1] for crop in area_crops)
                max_height = max(crop[1].shape[0] for crop in area_crops)
                
                # Create combined image
                combined_frame = np.zeros((max_height, total_width), dtype=np.uint8)
                
                # Place each crop side by side
                x_offset = 0
                for name, crop in area_crops:
                    h, w = crop.shape
                    combined_frame[:h, x_offset:x_offset+w] = crop
                    x_offset += w
            
            Image.fromarray(combined_frame, mode='L').save(output_file)
            return True
            
    except Exception:
        return False

def main():
    config = load_config()
    glacier_areas = config['area']['glacier_areas']
    
    tif_dir = Path(config['directories']['satellite_data'])
    output_dir = Path("out/glacier_aoi")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    vv_files = list(tif_dir.glob("*_VV.tif"))
    successful = 0
    
    print(f"Cropping to glacier coordinates from config.yaml")
    print(f"Areas: {len(glacier_areas)}")
    
    for tif_file in tqdm(sorted(vv_files), desc="Cropping to glacier area"):
        date_str = parse_date_from_name(tif_file.name)
        if not date_str:
            continue
            
        png_file = output_dir / f"{date_str}.png"
        if png_file.exists():
            successful += 1
            continue
            
        if crop_and_combine_areas(tif_file, glacier_areas, png_file):
            successful += 1
    
    print(f"Created {successful} glacier cropped frames in {output_dir}")

if __name__ == "__main__":
    main()