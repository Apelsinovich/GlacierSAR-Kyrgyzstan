"""
Simple script to convert Sentinel-1 ZIP files to PNG images.
This reads the raw data directly without needing SNAP processing.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

### USER SETTINGS ###

# Input folder with downloaded Sentinel-1 data
input_folder = '../kyrgyzstan_glacier_data'

# Output folder for PNG images
output_folder = '../sentinel_pngs_highres'

# Which polarization to use (VV or VH)
# VV is better for glacier/ice detection
polarization = 'vv'

# Image enhancement settings
contrast_percentile = (2, 98)  # Percentile for contrast stretching
colormap = 'gray'  # gray, viridis, terrain, etc.

# High resolution output settings
output_dpi = 300  # Higher DPI for better quality (default was 150)
save_full_resolution = True  # Save at native sensor resolution

### END OF USER SETTINGS ###


def setup_output_folder():
    """Create output folder if it doesn't exist."""
    Path(output_folder).mkdir(parents=True, exist_ok=True)


def find_tiff_files(zip_path, polarization='vv'):
    """Find measurement TIFF files in the Sentinel-1 ZIP."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        files = z.namelist()

        # Look for measurement TIFF files with the specified polarization
        tiff_files = [f for f in files if 'measurement' in f.lower()
                     and f.lower().endswith('.tiff')
                     and polarization.lower() in f.lower()]

        return tiff_files


def read_tiff_from_zip(zip_path, tiff_file):
    """Read TIFF data from ZIP file."""
    try:
        from PIL import Image
        import io

        # Increase PIL's image size limit to handle large Sentinel-1 images
        Image.MAX_IMAGE_PIXELS = None  # Remove limit entirely

        with zipfile.ZipFile(zip_path, 'r') as z:
            with z.open(tiff_file) as tiff_data:
                # Read the TIFF file
                img = Image.open(io.BytesIO(tiff_data.read()))
                # Convert to numpy array
                data = np.array(img)
                return data
    except Exception as e:
        print(f"  Error reading TIFF: {e}")
        return None


def enhance_contrast(data, percentile=(2, 98)):
    """Enhance contrast by clipping to percentiles."""
    valid_data = data[data > 0]  # Exclude zeros

    if len(valid_data) == 0:
        return data

    p_low, p_high = np.percentile(valid_data, percentile)

    # Clip and normalize
    data_clipped = np.clip(data, p_low, p_high)
    data_normalized = (data_clipped - p_low) / (p_high - p_low)

    return data_normalized


def create_png_simple(zip_path, output_path, polarization='vv', colormap='gray'):
    """
    Simple method: Extract and convert TIFF to PNG.
    """
    print(f"Processing: {zip_path.name}")

    # Find TIFF files
    tiff_files = find_tiff_files(zip_path, polarization)

    if not tiff_files:
        print(f"  ✗ No {polarization.upper()} measurement files found")
        return False

    print(f"  Found {len(tiff_files)} measurement file(s)")

    # Read the first TIFF file
    tiff_file = tiff_files[0]
    print(f"  Reading: {Path(tiff_file).name}")

    data = read_tiff_from_zip(zip_path, tiff_file)

    if data is None:
        return False

    print(f"  Data shape: {data.shape}")
    print(f"  Data range: {data.min():.2f} to {data.max():.2f}")

    # Convert to dB (log scale)
    data_db = 10 * np.log10(data + 1e-10)  # Add small value to avoid log(0)

    # Enhance contrast
    print("  Enhancing contrast...")
    data_enhanced = enhance_contrast(data_db, contrast_percentile)

    # Convert to 8-bit image for smaller file size
    data_8bit = (data_enhanced * 255).astype(np.uint8)

    # Create PIL Image directly (much smaller file size than matplotlib)
    img = Image.fromarray(data_8bit, mode='L')

    # Add metadata text
    date_str = zip_path.stem.split('_')[4][:8]

    # Save with compression
    print(f"  Saving image...")
    img.save(output_path, 'PNG', optimize=True, compress_level=9)

    # Check file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  File size: {file_size_mb:.2f} MB")

    # If file is too large, downsample
    max_size_mb = 30
    if file_size_mb > max_size_mb:
        print(f"  File exceeds {max_size_mb} MB, downsampling...")
        scale_factor = np.sqrt(max_size_mb / file_size_mb)
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img_resized.save(output_path, 'PNG', optimize=True, compress_level=9)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Resized to: {new_width}x{new_height}")
        print(f"  New file size: {file_size_mb:.2f} MB")

    print(f"  ✓ Saved to: {output_path.name}")
    return True


def create_png_quicklook(zip_path, output_path):
    """
    Quick method: Extract existing quicklook/preview images from the ZIP.
    This is the FASTEST method - no processing needed!
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            files = z.namelist()

            # Look for quicklook or preview PNG files
            preview_files = [f for f in files if 'quick-look.png' in f.lower()
                           or 'preview' in f.lower() and f.lower().endswith('.png')]

            if preview_files:
                preview_file = preview_files[0]
                print(f"  Extracting quicklook: {Path(preview_file).name}")

                # Extract and save
                with z.open(preview_file) as src:
                    with open(output_path, 'wb') as dst:
                        dst.write(src.read())

                print(f"  ✓ Saved to: {output_path.name}")
                return True
            else:
                return False
    except Exception as e:
        print(f"  ✗ Error extracting quicklook: {e}")
        return False


def convert_all_to_png(use_quicklook=True):
    """
    Convert all Sentinel-1 ZIP files to PNG.

    Args:
        use_quicklook: If True, use built-in quicklook images (fastest)
                       If False, process raw TIFF data (more control)
    """
    setup_output_folder()

    # Find all ZIP files
    input_path = Path(input_folder)
    zip_files = sorted(input_path.glob('S1*.zip'))

    if not zip_files:
        print(f"No Sentinel-1 files found in {input_folder}")
        return

    print(f"Found {len(zip_files)} Sentinel-1 files")
    print(f"Output folder: {output_folder}\n")

    if use_quicklook:
        print("Mode: Using built-in quicklook images (fastest)\n")
    else:
        print(f"Mode: Processing raw {polarization.upper()} data\n")

    successful = 0
    failed = 0
    skipped = 0

    for i, zip_file in enumerate(zip_files, 1):
        # Generate output filename
        date_str = zip_file.stem.split('_')[4][:8]

        if use_quicklook:
            output_name = f"{zip_file.stem}_quicklook.png"
        else:
            output_name = f"{zip_file.stem}_{polarization.upper()}.png"

        output_path = Path(output_folder) / output_name

        # Skip if already exists
        if output_path.exists():
            print(f"[{i}/{len(zip_files)}] Skipping (already exists): {zip_file.name}")
            skipped += 1
            continue

        print(f"\n[{i}/{len(zip_files)}] {zip_file.name}")

        # Convert
        if use_quicklook:
            success = create_png_quicklook(zip_file, output_path)

            # Fallback to raw data if quicklook not available
            if not success:
                print("  No quicklook found, processing raw data instead...")
                output_path = Path(output_folder) / f"{zip_file.stem}_{polarization.upper()}.png"
                success = create_png_simple(zip_file, output_path, polarization, colormap)
        else:
            success = create_png_simple(zip_file, output_path, polarization, colormap)

        if success:
            successful += 1
        else:
            failed += 1

    # Summary
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    print(f"✓ Successfully converted: {successful}")
    print(f"→ Skipped (already exists): {skipped}")
    if failed > 0:
        print(f"✗ Failed: {failed}")
    print(f"\nOutput folder: {output_folder}/")


def main():
    """Main function."""
    print("="*60)
    print("SENTINEL-1 TO PNG CONVERTER - HIGH RESOLUTION MODE")
    print("="*60)
    print("\nThis script offers two methods:")
    print("1. QUICKLOOK mode (fastest) - uses built-in preview images (low-res)")
    print("2. RAW DATA mode - processes measurement data with custom settings (HIGH-RES)")
    print()

    # Changed to False to process high-resolution raw data
    use_quicklook = False

    convert_all_to_png(use_quicklook=use_quicklook)


if __name__ == '__main__':
    main()
