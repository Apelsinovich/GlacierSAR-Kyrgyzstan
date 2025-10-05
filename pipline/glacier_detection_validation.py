#!/usr/bin/env python3
"""
Glacier Detection Validation - Show Real Detection Accuracy
Focus on actual glacier detection quality, not predictions
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import rasterio
import rasterio.warp
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_DIR = Path("out/satellite_data")
OUTPUT_DIR = Path("out/glacier_detection_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier area bounds (from previous analysis)
GLACIER_BOUNDS = {
    'min_lon': 74.4, 'max_lon': 74.6,
    'min_lat': 42.45, 'max_lat': 42.6
}

def extract_year_from_sar_filename(filename):
    """Extract year from SAR filename"""
    import re
    match = re.search(r'(20\d{2})\d{4}', str(filename))
    if match:
        return int(match.group(1))
    return None

def crop_to_glacier_area(data, src_profile, bounds):
    """Crop data to glacier area based on geographic bounds"""
    from rasterio.warp import transform_bounds
    from rasterio.transform import rowcol
    
    # Transform glacier bounds to image CRS
    file_bounds = transform_bounds("EPSG:4326", src_profile['crs'], *bounds)
    min_x, min_y, max_x, max_y = file_bounds
    
    # Convert to pixel coordinates
    transform = src_profile['transform']
    min_row, min_col = rowcol(transform, min_x, max_y)  # top-left
    max_row, max_col = rowcol(transform, max_x, min_y)  # bottom-right
    
    # Ensure within image bounds
    min_row, max_row = max(0, min_row), min(data.shape[0], max_row)
    min_col, max_col = max(0, min_col), min(data.shape[1], max_col)
    
    # Crop data
    cropped = data[min_row:max_row, min_col:max_col]
    
    # Update transform for cropped area
    new_transform = src_profile['transform'] * rasterio.Affine.translation(min_col, min_row)
    
    return cropped, new_transform, (min_row, max_row, min_col, max_col)

def load_and_crop_sar():
    """Load and crop SAR data using same logic as working script"""
    import glob
    
    # Find VV SAR files
    files = sorted(glob.glob(f"{DATA_DIR}/*_VV.tif"))
    print(f"📂 Found {len(files)} SAR files")
    
    # Extract years
    file_years = []
    valid_files = []
    for f in files:
        year = extract_year_from_sar_filename(f)
        if year:
            file_years.append(year)
            valid_files.append(f)
    
    # Sort by year
    sorted_data = sorted(zip(file_years, valid_files))
    years = [y for y, f in sorted_data]
    files = [f for y, f in sorted_data]
    
    print(f"� Processing years: {years}")
    
    # Convert bounds to tuple format
    bounds_tuple = (GLACIER_BOUNDS['min_lon'], GLACIER_BOUNDS['min_lat'], 
                   GLACIER_BOUNDS['max_lon'], GLACIER_BOUNDS['max_lat'])
    
    # Load first file to get dimensions
    with rasterio.open(files[0]) as ds0:
        full_data = ds0.read(1).astype("float32")
        full_profile = ds0.profile
        
        # Crop to glacier area
        cropped_sample, crop_transform, crop_coords = crop_to_glacier_area(
            full_data, full_profile, bounds_tuple
        )
        
        H, W = cropped_sample.shape
        print(f"🎯 Cropped to glacier area: {W}x{H} pixels")
    
    # Load all cropped data
    stack = []
    for t, f in enumerate(files):
        print(f"📖 Loading {Path(f).name} ({years[t]})")
        
        with rasterio.open(f) as ds:
            full_arr = ds.read(1).astype("float32")
            
            # Handle nodata
            if ds.nodata is not None:
                full_arr = np.where(full_arr == ds.nodata, np.nan, full_arr)
            
            # Convert to dB if needed (OPERA products are linear power)
            valid_data = full_arr[~np.isnan(full_arr)]
            if len(valid_data) > 0 and np.max(valid_data) > 10:  # Likely linear scale
                full_arr = np.where(full_arr > 0, 10 * np.log10(full_arr), np.nan)
            
            # Crop to glacier area
            cropped_data, _, _ = crop_to_glacier_area(full_arr, ds.profile, bounds_tuple)
            stack.append(cropped_data)
    
    print(f"✅ Loaded {len(stack)} SAR images")
    
    return np.array(stack), years

def detect_glacier_multilevel(sar_data, year):
    """
    Detect glaciers using 3-level approach
    Returns individual level masks and combined result
    """
    x = sar_data.copy()
    valid = np.isfinite(x)
    
    if np.sum(valid) == 0:
        return None, None, None, None
    
    print(f"\n🔍 Analyzing {year}:")
    print(f"    SAR range: {np.nanmin(x):.2f} to {np.nanmax(x):.2f} dB")
    
    # 3-Level Glacier Classification
    level3_th = np.percentile(x[valid], 12)   # Deep blue areas (darkest)
    level2_th = np.percentile(x[valid], 25)   # Green areas (medium)
    level1_th = np.percentile(x[valid], 40)   # Yellow areas (lightest)
    
    # Create individual level masks
    level3_mask = (x <= level3_th) & valid    # Deep blue glaciers
    level2_mask = (x <= level2_th) & valid    # Green glaciers
    level1_mask = (x <= level1_th) & valid    # Yellow glaciers
    
    # Noise reduction
    kernel = np.ones((2,2), dtype=bool)
    level3_mask = ndimage.binary_closing(level3_mask, structure=kernel)
    level2_mask = ndimage.binary_closing(level2_mask, structure=kernel)
    level1_mask = ndimage.binary_closing(level1_mask, structure=kernel)
    
    # Combined mask
    combined_mask = level1_mask  # Includes all levels
    
    # Statistics
    level3_count = np.sum(level3_mask)
    level2_count = np.sum(level2_mask) 
    level1_count = np.sum(level1_mask)
    total_pixels = np.sum(valid)
    
    print(f"    Level 3 (Deep Blue): {level3_count} pixels ({level3_th:.2f} dB) - {level3_count/total_pixels*100:.1f}%")
    print(f"    Level 2 (Green): {level2_count} pixels ({level2_th:.2f} dB) - {level2_count/total_pixels*100:.1f}%") 
    print(f"    Level 1 (Yellow): {level1_count} pixels ({level1_th:.2f} dB) - {level1_count/total_pixels*100:.1f}%")
    print(f"    Total Glacier: {level1_count} pixels ({level1_count/total_pixels*100:.1f}%)")
    
    return level3_mask, level2_mask, level1_mask, combined_mask

def create_detection_visualization(sar_img, level3_mask, level2_mask, level1_mask, combined_mask, year, save_path):
    """Create comprehensive detection visualization"""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Glacier Detection Analysis - {year}', fontsize=16, fontweight='bold')
    
    # 1. Original SAR image with good contrast
    valid_data = sar_img[np.isfinite(sar_img)]
    vmin, vmax = np.percentile(valid_data, [2, 98])
    
    im1 = axes[0,0].imshow(sar_img, cmap='gray', vmin=vmin, vmax=vmax)
    axes[0,0].set_title(f'Original SAR Image {year}\nRange: {np.nanmin(sar_img):.1f} to {np.nanmax(sar_img):.1f} dB')
    axes[0,0].axis('off')
    plt.colorbar(im1, ax=axes[0,0], fraction=0.046, pad=0.04)
    
    # 2. SAR histogram with thresholds
    axes[0,1].hist(valid_data, bins=50, alpha=0.7, color='lightblue', density=True)
    level3_th = np.percentile(valid_data, 12)
    level2_th = np.percentile(valid_data, 25) 
    level1_th = np.percentile(valid_data, 40)
    
    axes[0,1].axvline(level3_th, color='darkblue', linestyle='--', linewidth=2, label=f'Level 3: {level3_th:.1f} dB')
    axes[0,1].axvline(level2_th, color='green', linestyle='--', linewidth=2, label=f'Level 2: {level2_th:.1f} dB')
    axes[0,1].axvline(level1_th, color='gold', linestyle='--', linewidth=2, label=f'Level 1: {level1_th:.1f} dB')
    
    axes[0,1].set_title('SAR Value Distribution\nwith Detection Thresholds')
    axes[0,1].set_xlabel('SAR Value (dB)')
    axes[0,1].set_ylabel('Density')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # 3. Multi-level detection overlay
    axes[0,2].imshow(sar_img, cmap='gray', vmin=vmin, vmax=vmax, alpha=0.7)
    
    # Create colored overlay for each level
    overlay = np.zeros((*sar_img.shape, 3))
    overlay[level3_mask] = [0, 0, 0.8]      # Deep blue for level 3
    overlay[level2_mask & ~level3_mask] = [0, 0.8, 0]  # Green for level 2 only
    overlay[level1_mask & ~level2_mask] = [0.8, 0.8, 0]  # Yellow for level 1 only
    
    axes[0,2].imshow(overlay, alpha=0.6)
    axes[0,2].set_title('Multi-Level Detection Overlay\nBlue=L3, Green=L2, Yellow=L1')
    axes[0,2].axis('off')
    
    # 4. Level 3 Detection (Deep Blue - Darkest glaciers)
    detection_display = np.zeros_like(sar_img)
    detection_display[level3_mask] = 1
    axes[1,0].imshow(sar_img, cmap='gray', vmin=vmin, vmax=vmax, alpha=0.6)
    axes[1,0].imshow(detection_display, cmap='Blues', alpha=0.8, vmin=0, vmax=1)
    axes[1,0].set_title(f'Level 3: Deep Blue Areas\n{np.sum(level3_mask)} pixels ({np.sum(level3_mask)/level3_mask.size*100:.1f}%)')
    axes[1,0].axis('off')
    
    # 5. Level 2 Detection (Green - Medium glaciers)  
    detection_display = np.zeros_like(sar_img)
    detection_display[level2_mask] = 1
    axes[1,1].imshow(sar_img, cmap='gray', vmin=vmin, vmax=vmax, alpha=0.6)
    axes[1,1].imshow(detection_display, cmap='Greens', alpha=0.8, vmin=0, vmax=1)
    axes[1,1].set_title(f'Level 2: Green Areas\n{np.sum(level2_mask)} pixels ({np.sum(level2_mask)/level2_mask.size*100:.1f}%)')
    axes[1,1].axis('off')
    
    # 6. Complete glacier detection
    detection_display = np.zeros_like(sar_img)
    detection_display[combined_mask] = 1
    axes[1,2].imshow(sar_img, cmap='gray', vmin=vmin, vmax=vmax, alpha=0.6)
    axes[1,2].imshow(detection_display, cmap='Reds', alpha=0.8, vmin=0, vmax=1)
    axes[1,2].set_title(f'Complete Glacier Detection\n{np.sum(combined_mask)} pixels ({np.sum(combined_mask)/combined_mask.size*100:.1f}%)')
    axes[1,2].axis('off')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"    💾 Saved detection analysis: {save_path.name}")

def main():
    print("🔍 Glacier Detection Validation")
    print("=" * 50)
    
    # Load SAR data
    print("\n📂 Loading SAR data...")
    stack, years = load_and_crop_sar()
    
    print(f"\n🎭 Analyzing glacier detection for {len(years)} years...")
    
    # Process each year
    for i, year in enumerate(years):
        print(f"\n{'='*60}")
        print(f"Processing {year} ({i+1}/{len(years)})")
        print(f"{'='*60}")
        
        sar_img = stack[i]
        
        # Detect glaciers
        level3_mask, level2_mask, level1_mask, combined_mask = detect_glacier_multilevel(sar_img, year)
        
        if combined_mask is not None:
            # Create visualization 
            save_path = OUTPUT_DIR / f"glacier_detection_{year}.png"
            create_detection_visualization(
                sar_img, level3_mask, level2_mask, level1_mask, combined_mask, 
                year, save_path
            )
    
    print(f"\n🎉 Glacier Detection Validation Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📊 Generated {len(years)} detection analysis images")
    print(f"\n🔍 Check the images to validate detection accuracy:")
    for year in years:
        print(f"   • glacier_detection_{year}.png")

if __name__ == "__main__":
    main()