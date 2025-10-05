import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import rasterio
import glob
from pathlib import Path
import yaml
import os
import pandas as pd
from scipy.ndimage import binary_erosion, binary_dilation, binary_opening, binary_closing
from scipy.ndimage import label, distance_transform_edt
import shutil

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def pixel_to_db(pixel_values, db_min=-25.0, db_max=0.0):
    """Convert pixel values (0-255) back to dB values"""
    return (pixel_values / 255.0) * (db_max - db_min) + db_min

def detect_shadows_and_rock(db_data, pixel_data):
    """
    Detect shadows, rock formations, and terrain artifacts
    Bottom 1-5% are likely shadows/rock, not glacier ice
    """
    H, W = pixel_data.shape
    
    # Very dark threshold - likely shadows, rock formations, terrain artifacts
    very_dark_threshold = np.percentile(db_data[pixel_data > 0], 1)  # Bottom 1%
    shadow_threshold = np.percentile(db_data[pixel_data > 0], 5)     # Bottom 5%
    
    # Classify very dark areas
    shadows_rock = db_data <= very_dark_threshold
    dark_terrain = (db_data > very_dark_threshold) & (db_data <= shadow_threshold)
    
    # Clean up with morphology
    from scipy.ndimage import label, binary_opening, binary_closing
    
    # Remove tiny scattered pixels
    cleaned_shadows = binary_opening(shadows_rock, structure=np.ones((3,3)))
    cleaned_terrain = binary_opening(dark_terrain, structure=np.ones((3,3)))
    
    return cleaned_shadows, cleaned_terrain, very_dark_threshold, shadow_threshold

def create_highres_6level_for_year(pixel_data, db_data, filename, year, year_output_dir, 
                                   shadows_rock, dark_terrain, shadow_threshold, very_dark_threshold,
                                   p10, p25, p45, p65, p85, valid_db, total_valid):
    """
    Create high-resolution 6-level classification images for a specific year
    Corrected: darkest areas = shadows/rock, not deep ice
    """
    # Create 6-level classification - CORRECTED LOGIC
    shadows_rock_mask = shadows_rock & (pixel_data > 0)      # Very dark = shadows/rock
    dark_terrain_mask = dark_terrain & (pixel_data > 0)      # Dark terrain/rock
    deep_glacier = (db_data > shadow_threshold) & (db_data <= p10)   # Deep glacier ice (above shadows)
    regular_glacier = (db_data > p10) & (db_data <= p25)     # Regular glacier ice
    clean_glacier = (db_data > p25) & (db_data <= p45)       # Clean glacier ice  
    mixed_snow = (db_data > p45) & (db_data <= p65)          # Snow/mixed
    debris_rock = db_data > p65                               # Debris and bright rock
    
    # Calculate statistics
    shadows_rock_count = np.sum(shadows_rock_mask)
    dark_terrain_count = np.sum(dark_terrain_mask)
    deep_glacier_count = np.sum(deep_glacier)
    regular_glacier_count = np.sum(regular_glacier)
    clean_glacier_count = np.sum(clean_glacier)
    mixed_snow_count = np.sum(mixed_snow)
    debris_rock_count = np.sum(debris_rock)
    
    shadows_rock_percent = (shadows_rock_count / total_valid) * 100
    dark_terrain_percent = (dark_terrain_count / total_valid) * 100
    deep_glacier_percent = (deep_glacier_count / total_valid) * 100  
    regular_glacier_percent = (regular_glacier_count / total_valid) * 100
    clean_glacier_percent = (clean_glacier_count / total_valid) * 100
    mixed_snow_percent = (mixed_snow_count / total_valid) * 100
    debris_rock_percent = (debris_rock_count / total_valid) * 100
    
    # Create high-resolution 6-level classification image
    classification = np.zeros((*db_data.shape, 3), dtype=np.uint8)
    
    # Apply the 6 colors - CORRECTED COLOR SCHEME
    classification[shadows_rock_mask] = [0, 0, 0]          # Black - Shadows/rock (very dark)
    classification[dark_terrain_mask] = [64, 64, 64]       # Dark gray - Dark terrain
    classification[deep_glacier] = [0, 0, 139]             # Dark blue - Deep glacier ice
    classification[regular_glacier] = [0, 100, 255]        # Blue - Regular glacier ice
    classification[clean_glacier] = [0, 191, 255]          # Light blue - Clean glacier ice
    classification[mixed_snow] = [255, 255, 255]           # White - Snow/mixed
    classification[debris_rock] = [255, 165, 0]            # Orange - Debris/bright rock
    
    # 1. Create pure 6-level classification image (no text)
    pure_output_file = f"{year_output_dir}/pure_6level_classification_{year}.png"
    from PIL import Image
    classification_img = Image.fromarray(classification, mode='RGB')
    classification_img.save(pure_output_file, dpi=(300, 300))
    
    # 2. Create high-resolution figure with detailed legend
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Display the 6-level classification
    ax.imshow(classification)
    ax.set_title(f'Corrected 6-Level Glacier Classification - {year}\nAla-Archa Glacier SAR Analysis', 
                 fontsize=20, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Create detailed legend with statistics
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor='black', edgecolor='white', 
                     label=f'Shadows/Rock: {shadows_rock_percent:.1f}% ({shadows_rock_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='darkgray', edgecolor='black',
                     label=f'Dark Terrain: {dark_terrain_percent:.1f}% ({dark_terrain_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='darkblue', edgecolor='black',
                     label=f'Deep Glacier Ice: {deep_glacier_percent:.1f}% ({deep_glacier_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='blue', edgecolor='black',
                     label=f'Regular Ice: {regular_glacier_percent:.1f}% ({regular_glacier_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='lightblue', edgecolor='black',
                     label=f'Clean Ice: {clean_glacier_percent:.1f}% ({clean_glacier_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='white', edgecolor='black',
                     label=f'Snow/Mixed: {mixed_snow_percent:.1f}% ({mixed_snow_count:,} pixels)'),
        plt.Rectangle((0,0),1,1, facecolor='orange', edgecolor='black',
                     label=f'Debris/Rock: {debris_rock_percent:.1f}% ({debris_rock_count:,} pixels)')
    ]
    
    # Add legend outside the plot
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5), 
              fontsize=12, frameon=True, fancybox=True, shadow=True)
    
    # Add comprehensive information text box
    total_glacier_count = (deep_glacier_count + regular_glacier_count + 
                          clean_glacier_count + mixed_snow_count)
    total_glacier_percent = (total_glacier_count / total_valid) * 100
    
    info_text = f"""Corrected 6-Level Classification Analysis ({year}):

Data Source: Sentinel-1 SAR (OPERA RTC)
dB Range: {np.min(valid_db):.1f} to {np.max(valid_db):.1f} dB
Mean dB: {np.mean(valid_db):.1f} ± {np.std(valid_db):.1f} dB
Total Pixels: {total_valid:,}

CORRECTED Classification Logic:
Darkest areas (P1) = Shadows/Rock formations, NOT ice
Dark areas (P1-P5) = Dark terrain/rock
Medium-dark areas = Actual glacier ice begins here

Total Glacier Area: {total_glacier_percent:.1f}%
(Only actual ice + snow, excluding shadows/rock)

Color Classification:
Black = Shadows/Rock (<= {very_dark_threshold:.1f} dB)
Dark Gray = Dark Terrain ({very_dark_threshold:.1f} to {shadow_threshold:.1f} dB)
Dark Blue = Deep Ice ({shadow_threshold:.1f} to {p10:.1f} dB)
Blue = Regular Ice ({p10:.1f} to {p25:.1f} dB)
Light Blue = Clean Ice ({p25:.1f} to {p45:.1f} dB)
White = Snow/Mixed ({p45:.1f} to {p65:.1f} dB)
Orange = Debris/Rock (>= {p65:.1f} dB)"""
    
    fig.text(0.02, 0.02, info_text, fontsize=10, fontfamily='monospace',
            bbox=dict(boxstyle="round,pad=0.8", facecolor="lightgray", alpha=0.9),
            verticalalignment='bottom')
    
    plt.tight_layout()
    plt.subplots_adjust(left=0.05, right=0.75, bottom=0.35)
    
    # Save high-resolution image with description
    highres_output_file = f"{year_output_dir}/highres_6level_with_description_{year}.png"
    plt.savefig(highres_output_file, dpi=300, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.2)
    plt.close()
    
    return pure_output_file, highres_output_file

def analyze_db_distribution_multilevel():
    """
    Analyze dB distribution with CORRECTED classification
    Darkest areas = shadows/rock, NOT deep glacier ice
    """
    config = load_config()
    
    # Input directory with cropped glacier PNGs
    input_dir = "out/glacier_cropped_from_frame_pngs"
    base_output_dir = "out/db_distribution_analysis"
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Create CSV output directory
    csv_output_dir = f"{base_output_dir}/csv_data_series"
    os.makedirs(csv_output_dir, exist_ok=True)
    
    # Create directory for all pure 6-level images
    pure_images_dir = f"{base_output_dir}/pure_6level_images_collection"
    os.makedirs(pure_images_dir, exist_ok=True)
    
    # Get all PNG files
    png_files = sorted(glob.glob(f"{input_dir}/*.png"))
    if not png_files:
        print(f"No PNG files found in {input_dir}")
        return
    
    print(f"Found {len(png_files)} cropped glacier images")
    print("CORRECTED: Darkest areas = shadows/rock, NOT deep ice")
    print("Creating corrected 6-level classification images")
    
    # Master data collection for time series analysis
    master_data = []
    
    # Process each image
    for png_file in png_files:
        filename = Path(png_file).stem
        year = filename.split('-')[0]  # Extract year from filename
        
        print(f"Processing {filename}...")
        
        # Create year-specific output directory
        year_output_dir = f"{base_output_dir}/year_{year}"
        os.makedirs(year_output_dir, exist_ok=True)
        
        # Load image as grayscale
        from PIL import Image
        img = Image.open(png_file).convert('L')
        pixel_data = np.array(img)
        
        # Convert pixel values to dB (approximate)
        db_min, db_max = config['processing']['db_range']
        db_data = pixel_to_db(pixel_data, db_min, db_max)
        
        # Calculate histogram and statistics
        valid_pixels = pixel_data[pixel_data > 0]  # Exclude black pixels
        valid_db = db_data[pixel_data > 0]
        
        if len(valid_pixels) == 0:
            continue
        
        # CORRECTED: Detect shadows and rock (not glacier ice)
        shadows_rock, dark_terrain, very_dark_threshold, shadow_threshold = detect_shadows_and_rock(db_data, pixel_data)
        
        # CORRECTED thresholds for glacier classification
        # Start glacier ice classification ABOVE the shadow threshold
        p10 = np.percentile(valid_db, 15)   # Deep glacier ice (above shadows)
        p25 = np.percentile(valid_db, 30)   # Regular glacier ice
        p45 = np.percentile(valid_db, 50)   # Clean glacier ice 
        p65 = np.percentile(valid_db, 70)   # Mixed ice/snow
        p85 = np.percentile(valid_db, 85)   # Debris/rock (bright)
        
        # Create CORRECTED 6-level classification
        shadows_rock_mask = shadows_rock & (pixel_data > 0)      # Very dark = shadows/rock
        dark_terrain_mask = dark_terrain & (pixel_data > 0)      # Dark terrain
        deep_glacier = (db_data > shadow_threshold) & (db_data <= p10)   # Deep glacier (above shadows)
        regular_glacier = (db_data > p10) & (db_data <= p25)     # Regular ice
        clean_glacier = (db_data > p25) & (db_data <= p45)       # Clean ice  
        mixed_snow = (db_data > p45) & (db_data <= p65)          # Snow/mixed
        debris_rock = db_data > p65                               # Debris/bright rock
        
        # Calculate counts and percentages
        total_valid = len(valid_pixels)
        shadows_rock_count = np.sum(shadows_rock_mask)
        dark_terrain_count = np.sum(dark_terrain_mask)
        deep_glacier_count = np.sum(deep_glacier)
        regular_glacier_count = np.sum(regular_glacier)
        clean_glacier_count = np.sum(clean_glacier)
        mixed_snow_count = np.sum(mixed_snow)
        debris_rock_count = np.sum(debris_rock)
        
        # Total glacier areas (ONLY actual ice + snow, NOT shadows/rock)
        total_glacier_count = (deep_glacier_count + regular_glacier_count + 
                              clean_glacier_count + mixed_snow_count)
        
        shadows_rock_percent = (shadows_rock_count / total_valid) * 100
        dark_terrain_percent = (dark_terrain_count / total_valid) * 100
        deep_glacier_percent = (deep_glacier_count / total_valid) * 100
        regular_glacier_percent = (regular_glacier_count / total_valid) * 100
        clean_glacier_percent = (clean_glacier_count / total_valid) * 100
        mixed_snow_percent = (mixed_snow_count / total_valid) * 100
        debris_rock_percent = (debris_rock_count / total_valid) * 100
        total_glacier_percent = (total_glacier_count / total_valid) * 100
        
        # Save detailed dB data to CSV for this year
        db_df = pd.DataFrame({
            'pixel_x': np.repeat(np.arange(pixel_data.shape[1]), pixel_data.shape[0]),
            'pixel_y': np.tile(np.arange(pixel_data.shape[0]), pixel_data.shape[1]),
            'pixel_value': pixel_data.flatten(),
            'db_value': db_data.flatten(),
            'surface_type': ['background'] * pixel_data.size
        })
        
        # Add CORRECTED surface type classification
        flat_shadows = shadows_rock_mask.flatten()
        flat_terrain = dark_terrain_mask.flatten()
        flat_deep = deep_glacier.flatten()
        flat_regular = regular_glacier.flatten() 
        flat_clean = clean_glacier.flatten()
        flat_mixed = mixed_snow.flatten()
        flat_debris = debris_rock.flatten()
        
        db_df.loc[flat_shadows, 'surface_type'] = 'shadows_rock'
        db_df.loc[flat_terrain, 'surface_type'] = 'dark_terrain'
        db_df.loc[flat_deep, 'surface_type'] = 'deep_glacier_ice'
        db_df.loc[flat_regular, 'surface_type'] = 'regular_glacier_ice'
        db_df.loc[flat_clean, 'surface_type'] = 'clean_glacier_ice'
        db_df.loc[flat_mixed, 'surface_type'] = 'mixed_snow_ice'
        db_df.loc[flat_debris, 'surface_type'] = 'debris_rock'
        
        # Filter out background pixels for CSV
        db_df_filtered = db_df[db_df['pixel_value'] > 0].copy()
        
        # Save individual year CSV
        csv_file = f"{year_output_dir}/db_data_series_{year}.csv"
        db_df_filtered.to_csv(csv_file, index=False)
        
        # Save distribution statistics CSV
        stats_df = pd.DataFrame({
            'statistic': ['min_db', 'max_db', 'mean_db', 'std_db', 'very_dark_threshold', 'shadow_threshold', 'p10', 'p25', 'p45', 'p65', 'p85',
                         'shadows_rock_percent', 'dark_terrain_percent', 'deep_glacier_percent', 'regular_glacier_percent', 
                         'clean_glacier_percent', 'mixed_snow_percent', 'debris_rock_percent', 'total_glacier_percent'],
            'value': [np.min(valid_db), np.max(valid_db), np.mean(valid_db), np.std(valid_db),
                     very_dark_threshold, shadow_threshold, p10, p25, p45, p65, p85, 
                     shadows_rock_percent, dark_terrain_percent, deep_glacier_percent, regular_glacier_percent,
                     clean_glacier_percent, mixed_snow_percent, debris_rock_percent, total_glacier_percent]
        })
        stats_csv_file = f"{year_output_dir}/db_statistics_{year}.csv"
        stats_df.to_csv(stats_csv_file, index=False)
        
        # CREATE CORRECTED HIGH-RESOLUTION 6-LEVEL IMAGES
        pure_file, highres_file = create_highres_6level_for_year(
            pixel_data, db_data, filename, year, year_output_dir,
            shadows_rock, dark_terrain, shadow_threshold, very_dark_threshold,
            p10, p25, p45, p65, p85, valid_db, total_valid
        )
        
        # COPY PURE 6-LEVEL IMAGE TO COLLECTION DIRECTORY
        pure_collection_file = f"{pure_images_dir}/pure_6level_classification_{year}.png"
        shutil.copy2(pure_file, pure_collection_file)
        
        # Collect data for master time series
        master_data.append({
            'year': int(year),
            'min_db': np.min(valid_db),
            'max_db': np.max(valid_db),
            'mean_db': np.mean(valid_db),
            'std_db': np.std(valid_db),
            'very_dark_threshold': very_dark_threshold,
            'shadow_threshold': shadow_threshold,
            'p10_threshold': p10,
            'p25_threshold': p25,
            'p45_threshold': p45,
            'p65_threshold': p65,
            'p85_threshold': p85,
            'shadows_rock_pixels': shadows_rock_count,
            'dark_terrain_pixels': dark_terrain_count,
            'deep_glacier_pixels': deep_glacier_count,
            'regular_glacier_pixels': regular_glacier_count,
            'clean_glacier_pixels': clean_glacier_count,
            'mixed_snow_pixels': mixed_snow_count,
            'debris_rock_pixels': debris_rock_count,
            'total_glacier_pixels': total_glacier_count,
            'shadows_rock_percent': shadows_rock_percent,
            'dark_terrain_percent': dark_terrain_percent,
            'deep_glacier_percent': deep_glacier_percent,
            'regular_glacier_percent': regular_glacier_percent,
            'clean_glacier_percent': clean_glacier_percent,
            'mixed_snow_percent': mixed_snow_percent,
            'debris_rock_percent': debris_rock_percent,
            'total_glacier_percent': total_glacier_percent,
            'total_valid_pixels': total_valid
        })
        
        # Create CORRECTED 6-panel visualization
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle(f'CORRECTED 6-Level Analysis - Darkest Areas = Shadows/Rock - {year}', fontsize=16, fontweight='bold')
        
        # Panel 1: Original image
        axes[0,0].imshow(pixel_data, cmap='gray', vmin=0, vmax=255)
        axes[0,0].set_title('Original SAR Image\n(Pixel Values 0-255)', fontweight='bold')
        axes[0,0].axis('off')
        
        # Panel 2: dB histogram with CORRECTED thresholds
        axes[0,1].hist(valid_db, bins=60, alpha=0.7, color='lightblue', edgecolor='black')
        axes[0,1].axvline(very_dark_threshold, color='black', linestyle='--', linewidth=2, label=f'Shadows/Rock: {very_dark_threshold:.1f} dB')
        axes[0,1].axvline(shadow_threshold, color='gray', linestyle='--', linewidth=2, label=f'Dark Terrain: {shadow_threshold:.1f} dB')
        axes[0,1].axvline(p10, color='darkblue', linestyle='--', linewidth=2, label=f'P15: {p10:.1f} dB (Deep Ice)')
        axes[0,1].axvline(p25, color='blue', linestyle='--', linewidth=2, label=f'P30: {p25:.1f} dB (Regular Ice)')
        axes[0,1].axvline(p45, color='cyan', linestyle='--', linewidth=2, label=f'P50: {p45:.1f} dB (Clean Ice)')
        axes[0,1].axvline(p65, color='green', linestyle='--', linewidth=2, label=f'P70: {p65:.1f} dB (Snow)')
        axes[0,1].axvline(p85, color='red', linestyle='--', linewidth=2, label=f'P85: {p85:.1f} dB (Debris)')
        axes[0,1].set_xlabel('dB Values')
        axes[0,1].set_ylabel('Pixel Count')
        axes[0,1].set_title('CORRECTED 6-Level Classification\nDarkest = Shadows/Rock', fontweight='bold')
        axes[0,1].legend(fontsize=6)
        axes[0,1].grid(True, alpha=0.3)
        
        # Panel 3: CORRECTED 6-level classification overlay
        classification = np.zeros((*db_data.shape, 3), dtype=np.uint8)
        classification[shadows_rock_mask] = [0, 0, 0]          # Black - Shadows/rock
        classification[dark_terrain_mask] = [64, 64, 64]       # Dark gray - Dark terrain
        classification[deep_glacier] = [0, 0, 139]             # Dark blue - Deep ice
        classification[regular_glacier] = [0, 100, 255]        # Blue - Regular ice
        classification[clean_glacier] = [0, 191, 255]          # Light blue - Clean ice
        classification[mixed_snow] = [255, 255, 255]           # White - Snow/mixed
        classification[debris_rock] = [255, 165, 0]            # Orange - Debris
        
        axes[0,2].imshow(classification)
        axes[0,2].set_title('CORRECTED 6-Level Classification\nBlack=Shadows, Blues=Ice', fontweight='bold')
        axes[0,2].axis('off')
        
        # Panel 4: Shadows and rock only
        shadow_display = np.zeros_like(pixel_data)
        shadow_display[shadows_rock_mask] = 255
        axes[1,0].imshow(shadow_display, cmap='Greys', vmin=0, vmax=255)
        axes[1,0].set_title(f'Shadows/Rock Only\n{shadows_rock_count:,} pixels ({shadows_rock_percent:.1f}%)', fontweight='bold')
        axes[1,0].axis('off')
        
        # Panel 5: All glacier ice types (EXCLUDING shadows/rock)
        all_glacier_display = np.zeros_like(pixel_data)
        all_glacier_display[deep_glacier | regular_glacier | clean_glacier] = 255
        axes[1,1].imshow(all_glacier_display, cmap='Blues', vmin=0, vmax=255)
        pure_ice_count = deep_glacier_count + regular_glacier_count + clean_glacier_count
        pure_ice_percent = (pure_ice_count / total_valid) * 100
        axes[1,1].set_title(f'Pure Glacier Ice Only\n{pure_ice_count:,} pixels ({pure_ice_percent:.1f}%)', fontweight='bold')
        axes[1,1].axis('off')
        
        # Panel 6: Complete glacier area (ice + snow, NO shadows/rock)
        complete_glacier_display = np.zeros_like(pixel_data)
        complete_glacier_display[deep_glacier | regular_glacier | clean_glacier | mixed_snow] = 255
        axes[1,2].imshow(complete_glacier_display, cmap='viridis', vmin=0, vmax=255)
        axes[1,2].set_title(f'Total Glacier Area\n{total_glacier_count:,} pixels ({total_glacier_percent:.1f}%)', fontweight='bold')
        axes[1,2].axis('off')
        
        # Add CORRECTED comprehensive statistics text box
        stats_text = f"""CORRECTED 6-Level Classification for {year}:
dB Range: {np.min(valid_db):.1f} to {np.max(valid_db):.1f} dB
Mean: {np.mean(valid_db):.1f} ± {np.std(valid_db):.1f} dB

CORRECTED Surface Types:
Shadows/Rock: {shadows_rock_percent:.1f}% (<= {very_dark_threshold:.1f} dB) - NOT ice
Dark Terrain: {dark_terrain_percent:.1f}% ({very_dark_threshold:.1f} to {shadow_threshold:.1f} dB)
Deep Glacier Ice: {deep_glacier_percent:.1f}% ({shadow_threshold:.1f} to {p10:.1f} dB)
Regular Ice: {regular_glacier_percent:.1f}% ({p10:.1f} to {p25:.1f} dB)
Clean Ice: {clean_glacier_percent:.1f}% ({p25:.1f} to {p45:.1f} dB)
Snow/Mixed: {mixed_snow_percent:.1f}% ({p45:.1f} to {p65:.1f} dB)
Debris/Rock: {debris_rock_percent:.1f}% (>= {p65:.1f} dB)

TOTAL GLACIER: {total_glacier_percent:.1f}% (ice + snow only, excluding shadows/rock)"""
        
        fig.text(0.02, 0.02, stats_text, fontsize=8, fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.32)
        
        # Save the CORRECTED 6-panel analysis
        output_file = f"{year_output_dir}/db_distribution_6level_corrected_{filename}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"Year {year} - CORRECTED Analysis Complete")
        print(f"   Shadows/Rock: {shadows_rock_percent:.1f}% | Pure Ice: {pure_ice_percent:.1f}% | Total Glacier: {total_glacier_percent:.1f}%")
    
    # Save master time series data
    master_df = pd.DataFrame(master_data)
    master_csv_file = f"{csv_output_dir}/master_time_series_corrected.csv"
    master_df.to_csv(master_csv_file, index=False)
    
    print(f"\nCORRECTED 6-Level Analysis Complete!")
    print(f"Main output directory: {base_output_dir}/")
    print(f"Pure 6-level images collection: {pure_images_dir}/")
    print(f"Key correction: Darkest areas now properly classified as shadows/rock, NOT deep ice")

if __name__ == "__main__":
    analyze_db_distribution_multilevel()