import os
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import zipfile

try:
    from snappy import ProductIO, GPF, HashMap, jpy
    SNAPPY_AVAILABLE = True
except ImportError:
    SNAPPY_AVAILABLE = False

# Try importing rasterio as an alternative for reading processed GeoTIFFs
try:
    import rasterio
    from rasterio.plot import show
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

### USER SETTINGS ###

# Input folder with downloaded Sentinel-1 data
input_folder = '../kyrgyzstan_glacier_data'

# Output folders
processed_folder = '../processed_sentinel1'
results_folder = '../glacier_analysis_results'

# DEM to use for terrain correction (when using SNAP)
dem_name = 'SRTM 3Sec'  # or 'ASTER 1sec GDEM'

# Pixel spacing in meters (10m is good for Sentinel-1)
pixel_spacing = 10.0

# Glacier detection threshold (backscatter in dB)
# Typical range for glaciers: -18 to -12 dB (adjust based on your data)
glacier_threshold_db = -15.0

# Minimum glacier area in pixels to filter out noise
min_glacier_pixels = 100

### END OF USER SETTINGS ###


def check_sentinel1_files():
    """Check what Sentinel-1 files are available."""
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"Input folder not found: {input_folder}")
        return []

    zip_files = sorted(input_path.glob('S1*.zip'))
    return zip_files


def inspect_sentinel1_file(zip_path):
    """Inspect contents of a Sentinel-1 ZIP file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            files = z.namelist()
            print(f"\nContents of {zip_path.name}:")
            for f in files[:10]:  # Show first 10 files
                print(f"  - {f}")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more files")
            return files
    except Exception as e:
        print(f"Error inspecting {zip_path.name}: {e}")
        return []


def analyze_with_rasterio(geotiff_path, threshold_db):
    """Analyze glacier from GeoTIFF using rasterio."""
    if not RASTERIO_AVAILABLE:
        return None

    try:
        with rasterio.open(geotiff_path) as src:
            data = src.read(1)  # Read first band

            # Create glacier mask
            glacier_mask = (data >= threshold_db).astype(np.uint8)

            # Filter small regions
            glacier_mask = filter_small_regions(glacier_mask, min_glacier_pixels)

            # Calculate area (pixel size from metadata)
            transform = src.transform
            pixel_size_m = abs(transform[0])  # Assuming square pixels

            return glacier_mask, data, pixel_size_m
    except Exception as e:
        print(f"Error analyzing {geotiff_path.name}: {e}")
        return None


def analyze_processed_geotiffs():
    """Analyze already-processed GeoTIFF files."""
    if not RASTERIO_AVAILABLE:
        print("rasterio is not available. Install with: pip install rasterio")
        return

    processed_path = Path(processed_folder)
    if not processed_path.exists():
        print(f"Processed folder not found: {processed_folder}")
        return

    tif_files = sorted(processed_path.glob('*.tif'))
    if not tif_files:
        print(f"No GeoTIFF files found in {processed_folder}")
        return

    setup_output_folders()
    glacier_areas = {}

    for tif_file in tif_files:
        print(f"\nAnalyzing: {tif_file.name}")

        # Extract date from filename
        try:
            filename = tif_file.stem
            date_str = filename.split('_')[4][:8]
            date = datetime.strptime(date_str, '%Y%m%d')
        except:
            print(f"  Warning: Could not parse date from {tif_file.name}")
            continue

        result = analyze_with_rasterio(tif_file, glacier_threshold_db)
        if result is None:
            continue

        glacier_mask, backscatter_data, pixel_size = result

        # Calculate area
        num_pixels = np.sum(glacier_mask)
        area_m2 = num_pixels * (pixel_size ** 2)
        area_km2 = area_m2 / 1_000_000
        glacier_areas[date] = area_km2

        print(f"  Date: {date.strftime('%Y-%m-%d')}")
        print(f"  Glacier area: {area_km2:.2f} km²")

        # Save glacier mask
        mask_output = Path(results_folder) / f"glacier_mask_{date.strftime('%Y%m%d')}.png"
        plt.figure(figsize=(10, 8))
        plt.imshow(glacier_mask, cmap='Blues')
        plt.title(f'Glacier Mask - {date.strftime("%Y-%m-%d")}')
        plt.colorbar(label='Glacier (1) / Non-glacier (0)')
        plt.savefig(mask_output, dpi=150, bbox_inches='tight')
        plt.close()

    if glacier_areas:
        plot_glacier_time_series(glacier_areas)
        save_glacier_statistics(glacier_areas)


def print_snap_instructions():
    """Print instructions for using SNAP."""
    print("\n" + "="*70)
    print("HOW TO PROCESS SENTINEL-1 DATA WITH SNAP")
    print("="*70)
    print("\n1. INSTALL SNAP:")
    print("   Download from: https://step.esa.int/main/download/snap-download/")
    print("   Choose 'SNAP Desktop' for macOS")

    print("\n2. PROCESS DATA IN SNAP GUI:")
    print("   For each S1*.zip file:")
    print("   a) File → Open Product → Select the .zip file")
    print("   b) Radar → Apply Orbit File")
    print("   c) Radar → Radiometric → Calibrate")
    print("      - Select 'Sigma0' output")
    print("   d) Radar → Speckle Filtering → Single Product Speckle Filter")
    print("      - Filter: 'Refined Lee', Size: 5x5")
    print("   e) Radar → Geometric → Terrain Correction → Range-Doppler Terrain Correction")
    print("      - DEM: 'SRTM 3Sec'")
    print("      - Pixel spacing: 10m")
    print("   f) Raster → Data Conversion → Linear to/from dB")
    print("   g) File → Export → GeoTIFF")
    print("      - Save to 'processed_sentinel1' folder")

    print("\n3. CONFIGURE SNAPPY (Optional - for Python automation):")
    print("   After installing SNAP, run:")
    print("   /Applications/snap/bin/snappy-conf $(which python)")

    print("\n4. RUN THIS SCRIPT AGAIN:")
    print("   After processing files, run this script to analyze glacier changes")
    print("="*70)


def setup_output_folders():
    """Create output folders if they don't exist."""
    Path(processed_folder).mkdir(parents=True, exist_ok=True)
    Path(results_folder).mkdir(parents=True, exist_ok=True)


def get_scene_date(product):
    """Extract acquisition date from product metadata."""
    try:
        start_time = product.getStartTime()
        date_str = start_time.format().split('T')[0]
        return datetime.strptime(date_str, '%d-%b-%Y')
    except:
        # Fallback: try to parse from filename
        name = product.getName()
        # Format: S1A_IW_GRDH_1SDV_20201222T125920_...
        date_part = name.split('_')[4][:8]
        return datetime.strptime(date_part, '%Y%m%d')


def process_sentinel1_scene(input_file, output_file):
    """
    Process a single Sentinel-1 scene through the complete workflow:
    1. Read product
    2. Apply precise orbit
    3. Thermal noise removal
    4. Calibration to sigma0
    5. Speckle filtering
    6. Terrain correction
    7. Convert to dB
    """
    if not SNAPPY_AVAILABLE:
        print(f"Skipping {Path(input_file).name} - snappy not available")
        return None

    print(f"\nProcessing: {Path(input_file).name}")

    try:
        # Read the product
        product = ProductIO.readProduct(str(input_file))

        # Step 1: Apply orbit file
        print("  - Applying orbit file...")
        params = HashMap()
        orbit_product = GPF.createProduct('Apply-Orbit-File', params, product)

        # Step 2: Thermal noise removal (important for glacier analysis)
        print("  - Removing thermal noise...")
        params = HashMap()
        params.put('removeThermalNoise', True)
        noise_product = GPF.createProduct('ThermalNoiseRemoval', params, orbit_product)

        # Step 3: Calibration to sigma0
        print("  - Calibrating to sigma0...")
        params = HashMap()
        params.put('outputSigmaBand', True)
        params.put('outputBetaBand', False)
        params.put('outputGammaBand', False)
        calib_product = GPF.createProduct('Calibration', params, noise_product)

        # Step 4: Speckle filtering (Refined Lee 5x5)
        print("  - Applying speckle filter...")
        params = HashMap()
        params.put('filter', 'Refined Lee')
        params.put('filterSizeX', 5)
        params.put('filterSizeY', 5)
        params.put('dampingFactor', 2)
        filtered_product = GPF.createProduct('Speckle-Filter', params, calib_product)

        # Step 5: Terrain correction
        print("  - Terrain correction...")
        params = HashMap()
        params.put('demName', dem_name)
        params.put('pixelSpacingInMeter', pixel_spacing)
        params.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
        params.put('mapProjection', 'AUTO:42001')  # WGS84 / Auto UTM
        terrain_product = GPF.createProduct('Terrain-Correction', params, filtered_product)

        # Step 6: Convert to dB
        print("  - Converting to dB...")
        params = HashMap()
        dB_product = GPF.createProduct('LinearToFromdB', params, terrain_product)

        # Write output
        print(f"  - Writing output to {Path(output_file).name}...")
        ProductIO.writeProduct(dB_product, str(output_file), 'GeoTIFF-BigTIFF')

        print("  ✓ Processing complete!")

        # Clean up
        product.dispose()
        orbit_product.dispose()
        noise_product.dispose()
        calib_product.dispose()
        filtered_product.dispose()
        terrain_product.dispose()

        return dB_product

    except Exception as e:
        print(f"  ✗ Error processing {Path(input_file).name}: {e}")
        return None


def extract_glacier_mask(geotiff_path, threshold_db):
    """
    Extract glacier mask from processed GeoTIFF using threshold.
    Returns numpy array with glacier pixels as 1, non-glacier as 0.
    """
    if not SNAPPY_AVAILABLE:
        return None

    try:
        product = ProductIO.readProduct(str(geotiff_path))

        # Get the Sigma0_VV band (or VH if available)
        band_names = product.getBandNames()
        band_name = None
        for name in band_names:
            if 'Sigma0_VV' in name or 'Sigma0_VH' in name:
                band_name = name
                break

        if band_name is None:
            print(f"Warning: No Sigma0 band found in {geotiff_path.name}")
            return None

        band = product.getBand(band_name)
        width = band.getRasterWidth()
        height = band.getRasterHeight()

        # Read band data
        data = np.zeros(width * height, dtype=np.float32)
        band.readPixels(0, 0, width, height, data)
        data = data.reshape((height, width))

        # Create glacier mask: values above threshold are likely glaciers
        # (in dB, higher values = brighter = more likely to be ice/snow)
        glacier_mask = (data >= threshold_db).astype(np.uint8)

        # Filter out small isolated pixels (noise)
        glacier_mask = filter_small_regions(glacier_mask, min_glacier_pixels)

        product.dispose()

        return glacier_mask, data

    except Exception as e:
        print(f"Error extracting glacier mask: {e}")
        return None


def filter_small_regions(mask, min_size):
    """Remove small isolated regions from binary mask."""
    try:
        from scipy import ndimage
        labeled, num_features = ndimage.label(mask)
        sizes = ndimage.sum(mask, labeled, range(num_features + 1))
        mask_filtered = sizes >= min_size
        return mask_filtered[labeled]
    except ImportError:
        print("Warning: scipy not available, skipping small region filtering")
        return mask


def calculate_glacier_area(mask, pixel_size_m):
    """Calculate glacier area in km² from binary mask."""
    num_pixels = np.sum(mask)
    area_m2 = num_pixels * (pixel_size_m ** 2)
    area_km2 = area_m2 / 1_000_000
    return area_km2


def analyze_glacier_changes(processed_files):
    """
    Analyze glacier area changes over time.
    """
    print("\n" + "=" * 50)
    print("ANALYZING GLACIER AREA CHANGES")
    print("=" * 50)

    glacier_areas = {}  # date -> area in km²

    for geotiff_path in processed_files:
        print(f"\nAnalyzing: {geotiff_path.name}")

        # Extract date from filename
        try:
            # Format: S1A_IW_GRDH_1SDV_20201222T125920_...
            filename = geotiff_path.stem
            date_str = filename.split('_')[4][:8]
            date = datetime.strptime(date_str, '%Y%m%d')
        except:
            print(f"  Warning: Could not parse date from {geotiff_path.name}")
            continue

        # Extract glacier mask
        result = extract_glacier_mask(geotiff_path, glacier_threshold_db)
        if result is None:
            continue

        glacier_mask, backscatter_data = result

        # Calculate area
        area_km2 = calculate_glacier_area(glacier_mask, pixel_spacing)
        glacier_areas[date] = area_km2

        print(f"  Date: {date.strftime('%Y-%m-%d')}")
        print(f"  Glacier area: {area_km2:.2f} km²")

        # Save glacier mask
        mask_output = Path(results_folder) / f"glacier_mask_{date.strftime('%Y%m%d')}.png"
        plt.figure(figsize=(10, 8))
        plt.imshow(glacier_mask, cmap='Blues')
        plt.title(f'Glacier Mask - {date.strftime("%Y-%m-%d")}')
        plt.colorbar(label='Glacier (1) / Non-glacier (0)')
        plt.savefig(mask_output, dpi=150, bbox_inches='tight')
        plt.close()

    # Create time series plot
    if glacier_areas:
        plot_glacier_time_series(glacier_areas)
        save_glacier_statistics(glacier_areas)

    return glacier_areas


def plot_glacier_time_series(glacier_areas):
    """Plot glacier area changes over time."""
    dates = sorted(glacier_areas.keys())
    areas = [glacier_areas[d] for d in dates]

    plt.figure(figsize=(14, 6))
    plt.plot(dates, areas, 'o-', linewidth=2, markersize=6)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Glacier Area (km²)', fontsize=12)
    plt.title('Glacier Area Changes Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = Path(results_folder) / 'glacier_area_timeseries.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Time series plot saved to: {output_path}")
    plt.close()

    # Calculate statistics
    if len(areas) > 1:
        initial_area = areas[0]
        final_area = areas[-1]
        change_km2 = final_area - initial_area
        change_percent = (change_km2 / initial_area) * 100

        print(f"\n{'=' * 50}")
        print("GLACIER CHANGE SUMMARY")
        print(f"{'=' * 50}")
        print(f"Period: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
        print(f"Initial area: {initial_area:.2f} km²")
        print(f"Final area: {final_area:.2f} km²")
        print(f"Change: {change_km2:+.2f} km² ({change_percent:+.1f}%)")
        if change_km2 < 0:
            print("⚠️  Glacier is RETREATING")
        elif change_km2 > 0:
            print("✓ Glacier is ADVANCING")
        else:
            print("→ Glacier is STABLE")


def save_glacier_statistics(glacier_areas):
    """Save detailed statistics to CSV file."""
    output_path = Path(results_folder) / 'glacier_statistics.csv'

    dates = sorted(glacier_areas.keys())

    with open(output_path, 'w') as f:
        f.write("Date,Glacier_Area_km2,Change_from_Previous_km2,Change_from_First_km2\n")

        for i, date in enumerate(dates):
            area = glacier_areas[date]

            if i == 0:
                change_prev = 0
                change_first = 0
            else:
                change_prev = area - glacier_areas[dates[i - 1]]
                change_first = area - glacier_areas[dates[0]]

            f.write(f"{date.strftime('%Y-%m-%d')},{area:.4f},{change_prev:.4f},{change_first:.4f}\n")

    print(f"✓ Statistics saved to: {output_path}")


def main():
    """Main processing workflow."""

    # Check what's available
    zip_files = check_sentinel1_files()

    if not zip_files:
        print(f"\nNo Sentinel-1 files found in {input_folder}")
        return

    print(f"Found {len(zip_files)} Sentinel-1 files")

    # Check if we have SNAP/snappy
    if not SNAPPY_AVAILABLE:
        print("\n⚠️  SNAP Python API (snappy) is not available")

        # Check if we have processed GeoTIFFs
        processed_path = Path(processed_folder)
        if processed_path.exists():
            tif_files = list(processed_path.glob('*.tif'))
            if tif_files:
                print(f"\n✓ Found {len(tif_files)} processed GeoTIFF files")
                print("Analyzing processed files...")
                analyze_processed_geotiffs()
                return

        print("\nNo processed GeoTIFF files found.")
        print("\nYou have two options:")
        print("\nOPTION 1: Process data manually with SNAP GUI")
        print_snap_instructions()

        print("\n\nOPTION 2: Install SNAP and configure snappy for automated processing")
        print("Then run this script again.")

        # Show a sample file inspection
        if zip_files:
            print("\n" + "="*70)
            print("SAMPLE FILE INSPECTION")
            print("="*70)
            inspect_sentinel1_file(zip_files[0])

        return

    # If snappy is available, run full processing
    setup_output_folders()

    input_path = Path(input_folder)
    zip_files = sorted(input_path.glob('S1*.zip'))

    print(f"Found {len(zip_files)} Sentinel-1 files to process\n")

    # Process each file
    processed_files = []

    for i, zip_file in enumerate(zip_files, 1):
        output_name = zip_file.stem + '_processed.tif'
        output_path = Path(processed_folder) / output_name

        # Skip if already processed
        if output_path.exists():
            print(f"[{i}/{len(zip_files)}] Skipping (already processed): {zip_file.name}")
            processed_files.append(output_path)
            continue

        print(f"\n[{i}/{len(zip_files)}] Processing: {zip_file.name}")

        result = process_sentinel1_scene(zip_file, output_path)

        if result is not None:
            processed_files.append(output_path)
            result.dispose()

    # Analyze glacier changes
    if processed_files:
        glacier_areas = analyze_glacier_changes(processed_files)

        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE!")
        print(f"{'='*60}")
        print(f"Processed files: {len(processed_files)}")
        print(f"Output folder: {processed_folder}/")
        print(f"Results folder: {results_folder}/")
    else:
        print("\nNo files were successfully processed.")


if __name__ == '__main__':
    main()
