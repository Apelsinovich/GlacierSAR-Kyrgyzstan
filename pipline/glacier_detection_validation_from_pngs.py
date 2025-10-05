#!/usr/bin/env python3
"""
Glacier Detection Validation - Using Pre-Cropped Glacier Images
Analyze real glacier detection accuracy on cropped glacier PNG files
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from scipy import ndimage
import cv2
import warnings
warnings.filterwarnings('ignore')

# Paths
CROPPED_DIR = Path("out/glacier_cropped_from_frame_pngs")
OUTPUT_DIR = Path("out/glacier_detection_validation_from_pngs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_cropped_glacier_images():
    """Load pre-cropped glacier PNG images"""
    png_files = sorted(CROPPED_DIR.glob("*.png"))
    print(f"📂 Found {len(png_files)} cropped glacier images")
    
    images = []
    years = []
    
    for f in png_files:
        # Extract year from filename (YYYY-MM-DD.png format)
        year_str = f.stem[:4]  # First 4 characters
        year = int(year_str)
        years.append(year)
        
        print(f"📖 Loading {f.name} ({year})")
        
        # Load image
        img = Image.open(f)
        img_array = np.array(img)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_array
            
        images.append(img_gray)
    
    print(f"✅ Loaded {len(images)} glacier images")
    print(f"📅 Years: {years}")
    if len(images) > 0:
        print(f"🎯 Image size: {images[0].shape[1]}x{images[0].shape[0]} pixels")
    
    return images, years

def detect_glacier_from_png(img_gray, year):
    """
    Detect glaciers from PNG image using visual characteristics
    Focus on detecting deep blue, green, and yellow glacier areas
    """
    print(f"\n🔍 Analyzing {year}:")
    print(f"    Image range: {img_gray.min()} to {img_gray.max()} (pixel values)")
    
    # Convert to float for processing
    img_float = img_gray.astype(float)
    
    # For glacier detection on RGB images converted to grayscale:
    # Darker areas (lower pixel values) = glaciers
    # We'll use inverse logic: lower values = more likely glacier
    
    # 3-Level Glacier Classification based on pixel darkness
    # Level 3: Darkest areas (deep blue glaciers)
    level3_th = np.percentile(img_float, 25)   # Darkest 25%
    
    # Level 2: Medium dark areas (green glaciers)  
    level2_th = np.percentile(img_float, 45)   # Darkest 45%
    
    # Level 1: Lighter dark areas (yellow/bright glaciers)
    level1_th = np.percentile(img_float, 65)   # Darkest 65%
    
    # Create individual level masks (lower values = glaciers)
    level3_mask = img_float <= level3_th    # Deep blue glaciers (darkest)
    level2_mask = img_float <= level2_th    # Green glaciers (medium)
    level1_mask = img_float <= level1_th    # Yellow glaciers (lightest)
    
    # Noise reduction
    kernel = np.ones((3,3), dtype=bool)
    level3_mask = ndimage.binary_closing(level3_mask, structure=kernel)
    level2_mask = ndimage.binary_closing(level2_mask, structure=kernel)
    level1_mask = ndimage.binary_closing(level1_mask, structure=kernel)
    
    # Remove small isolated areas
    level3_mask = ndimage.binary_opening(level3_mask, structure=kernel)
    level2_mask = ndimage.binary_opening(level2_mask, structure=kernel)
    level1_mask = ndimage.binary_opening(level1_mask, structure=kernel)
    
    # Combined mask
    combined_mask = level1_mask  # Includes all levels
    
    # Statistics
    total_pixels = img_float.size
    level3_count = np.sum(level3_mask)
    level2_count = np.sum(level2_mask) 
    level1_count = np.sum(level1_mask)
    
    print(f"    Level 3 (Deep Blue): {level3_count} pixels (≤{level3_th:.0f}) - {level3_count/total_pixels*100:.1f}%")
    print(f"    Level 2 (Green): {level2_count} pixels (≤{level2_th:.0f}) - {level2_count/total_pixels*100:.1f}%") 
    print(f"    Level 1 (Yellow): {level1_count} pixels (≤{level1_th:.0f}) - {level1_count/total_pixels*100:.1f}%")
    print(f"    Total Glacier: {level1_count} pixels ({level1_count/total_pixels*100:.1f}%)")
    
    return level3_mask, level2_mask, level1_mask, combined_mask, (level3_th, level2_th, level1_th)

def create_detection_visualization(original_img, level3_mask, level2_mask, level1_mask, combined_mask, thresholds, year, save_path):
    """Create comprehensive detection visualization for PNG glacier images"""
    
    level3_th, level2_th, level1_th = thresholds
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Glacier Detection Analysis - {year} (From Cropped PNG)', fontsize=16, fontweight='bold')
    
    # 1. Original image
    axes[0,0].imshow(original_img, cmap='gray')
    axes[0,0].set_title(f'Original Cropped Glacier Image {year}\nPixel range: {original_img.min()} to {original_img.max()}')
    axes[0,0].axis('off')
    
    # 2. Histogram with thresholds
    axes[0,1].hist(original_img.flatten(), bins=50, alpha=0.7, color='lightblue', density=True)
    
    axes[0,1].axvline(level3_th, color='darkblue', linestyle='--', linewidth=2, label=f'Level 3: ≤{level3_th:.0f}')
    axes[0,1].axvline(level2_th, color='green', linestyle='--', linewidth=2, label=f'Level 2: ≤{level2_th:.0f}')
    axes[0,1].axvline(level1_th, color='gold', linestyle='--', linewidth=2, label=f'Level 1: ≤{level1_th:.0f}')
    
    axes[0,1].set_title('Pixel Value Distribution\nwith Detection Thresholds')
    axes[0,1].set_xlabel('Pixel Value')
    axes[0,1].set_ylabel('Density')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # 3. Multi-level detection overlay on original image
    axes[0,2].imshow(original_img, cmap='gray', alpha=0.7)
    
    # Create colored overlay for each level
    overlay = np.zeros((*original_img.shape, 3))
    overlay[level3_mask] = [0, 0, 0.8]      # Deep blue for level 3
    overlay[level2_mask & ~level3_mask] = [0, 0.8, 0]  # Green for level 2 only  
    overlay[level1_mask & ~level2_mask] = [0.8, 0.8, 0]  # Yellow for level 1 only
    
    axes[0,2].imshow(overlay, alpha=0.6)
    axes[0,2].set_title('Multi-Level Detection Overlay\nBlue=Deep, Green=Medium, Yellow=Light')
    axes[0,2].axis('off')
    
    # 4. Level 3 Detection (Deep Blue - Darkest glaciers)
    detection_display = np.zeros_like(original_img)
    detection_display[level3_mask] = 255
    axes[1,0].imshow(original_img, cmap='gray', alpha=0.6)
    axes[1,0].imshow(detection_display, cmap='Blues', alpha=0.8, vmin=0, vmax=255)
    axes[1,0].set_title(f'Level 3: Deep Blue Areas\n{np.sum(level3_mask)} pixels ({np.sum(level3_mask)/level3_mask.size*100:.1f}%)')
    axes[1,0].axis('off')
    
    # 5. Level 2 Detection (Green - Medium glaciers)  
    detection_display = np.zeros_like(original_img)
    detection_display[level2_mask] = 255
    axes[1,1].imshow(original_img, cmap='gray', alpha=0.6)
    axes[1,1].imshow(detection_display, cmap='Greens', alpha=0.8, vmin=0, vmax=255)
    axes[1,1].set_title(f'Level 2: Green Areas\n{np.sum(level2_mask)} pixels ({np.sum(level2_mask)/level2_mask.size*100:.1f}%)')
    axes[1,1].axis('off')
    
    # 6. Complete glacier detection
    detection_display = np.zeros_like(original_img)
    detection_display[combined_mask] = 255
    axes[1,2].imshow(original_img, cmap='gray', alpha=0.6)
    axes[1,2].imshow(detection_display, cmap='Reds', alpha=0.8, vmin=0, vmax=255)
    axes[1,2].set_title(f'Complete Glacier Detection\n{np.sum(combined_mask)} pixels ({np.sum(combined_mask)/combined_mask.size*100:.1f}%)')
    axes[1,2].axis('off')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"    💾 Saved detection analysis: {save_path.name}")

def main():
    print("🔍 Glacier Detection Validation from Cropped PNGs")
    print("=" * 60)
    
    # Load cropped glacier images
    print("\n📂 Loading cropped glacier images...")
    images, years = load_cropped_glacier_images()
    
    if len(images) == 0:
        print("❌ No cropped glacier images found!")
        return
    
    print(f"\n🎭 Analyzing glacier detection for {len(years)} years...")
    
    # Process each year
    detection_results = []
    
    for i, year in enumerate(years):
        print(f"\n{'='*60}")
        print(f"Processing {year} ({i+1}/{len(years)})")
        print(f"{'='*60}")
        
        img = images[i]
        
        # Detect glaciers
        level3_mask, level2_mask, level1_mask, combined_mask, thresholds = detect_glacier_from_png(img, year)
        
        # Store results
        detection_results.append({
            'year': year,
            'total_pixels': img.size,
            'level3_count': np.sum(level3_mask),
            'level2_count': np.sum(level2_mask),
            'level1_count': np.sum(level1_mask),
            'glacier_percentage': np.sum(combined_mask) / img.size * 100
        })
        
        # Create visualization 
        save_path = OUTPUT_DIR / f"glacier_detection_png_{year}.png"
        create_detection_visualization(
            img, level3_mask, level2_mask, level1_mask, combined_mask, 
            thresholds, year, save_path
        )
    
    # Summary
    print(f"\n🎉 Glacier Detection Validation Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📊 Generated {len(years)} detection analysis images")
    
    print(f"\n📊 Detection Summary:")
    print("Year | Total Pixels | Level 3 | Level 2 | Level 1 | Glacier %")
    print("-" * 65)
    for result in detection_results:
        print(f"{result['year']} | {result['total_pixels']:>11} | {result['level3_count']:>7} | {result['level2_count']:>7} | {result['level1_count']:>7} | {result['glacier_percentage']:>7.1f}%")
    
    print(f"\n🔍 Check these PNG-based detection images:")
    for year in years:
        print(f"   • glacier_detection_png_{year}.png")

if __name__ == "__main__":
    main()