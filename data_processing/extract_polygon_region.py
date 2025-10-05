"""
Extract Sentinel-1 data for a specific polygon region and convert to PNG images.
Creates separate outputs for VV, VH, and HH polarizations.
"""

import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point
import pyproj
import rasterio
import tempfile
import os

### USER SETTINGS ###

# Input folder with downloaded Sentinel-1 data
input_folder = 'kyrgyzstan_glacier_data'

# Output base folder
output_base_folder = 'sentinel_polygon_pngs'

# Area of Interest (WKT polygon)
wkt_aoi = 'POLYGON ((74.487648 42.479187, 74.473057 42.475769, 74.474258 42.463613, 74.487648 42.436127, 74.510994 42.433846, 74.523869 42.448035, 74.503269 42.467032, 74.487648 42.479187))'

# Polarizations to extract
polarizations = ['vv', 'vh', 'hh']

# Image enhancement settings
contrast_percentile = (2, 98)

# Maximum file size in MB
max_file_size_mb = 32

### END OF USER SETTINGS ###


def parse_wkt_polygon(wkt):
    """Parse WKT polygon string to Shapely polygon."""
    from shapely import wkt as shapely_wkt
    return shapely_wkt.loads(wkt)


def setup_output_folders():
    """Create output folders for each polarization."""
    folders = {}
    for pol in polarizations:
        folder_path = Path(output_base_folder) / pol.upper()
        folder_path.mkdir(parents=True, exist_ok=True)
        folders[pol] = folder_path
    return folders


def find_tiff_files(zip_path, polarization):
    """Find measurement TIFF files for specific polarization in the Sentinel-1 ZIP."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        files = z.namelist()
        
        # Look for measurement TIFF files with the specified polarization
        tiff_files = [f for f in files if 'measurement' in f.lower()
                     and f.lower().endswith('.tiff')
                     and polarization.lower() in f.lower()]
        
        return tiff_files


def get_geolocation_grid(zip_path):
    """Extract geolocation grid from Sentinel-1 annotation XML."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Find annotation XML file
            xml_files = [f for f in z.namelist() if 'annotation/s1' in f.lower() and f.endswith('.xml')]

            if not xml_files:
                return None

            # Read first annotation file
            with z.open(xml_files[0]) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Find geolocation grid points
                grid_points = []
                for gcp in root.findall('.//geolocationGridPoint'):
                    try:
                        pixel = int(gcp.find('pixel').text)
                        line = int(gcp.find('line').text)
                        lat = float(gcp.find('latitude').text)
                        lon = float(gcp.find('longitude').text)
                        grid_points.append((pixel, line, lon, lat))
                    except:
                        continue

                return grid_points if grid_points else None
    except Exception as e:
        print(f"  Error reading geolocation grid: {e}")
        return None


def pixel_to_latlon_simple(pixel, line, grid_points):
    """Convert pixel/line to lat/lon using simple nearest neighbor interpolation."""
    if not grid_points:
        return None, None

    # Find closest grid point
    min_dist = float('inf')
    closest_point = None

    for gp in grid_points:
        gp_pixel, gp_line, gp_lon, gp_lat = gp
        dist = np.sqrt((pixel - gp_pixel)**2 + (line - gp_line)**2)
        if dist < min_dist:
            min_dist = dist
            closest_point = gp

    if closest_point:
        return closest_point[2], closest_point[3]  # lon, lat
    return None, None


def interpolate_latlon_to_pixel(lat, lon, grid_points):
    """
    Interpolate lat/lon to pixel coordinates using bilinear interpolation of the grid.
    """
    if not grid_points or len(grid_points) < 4:
        return None, None

    # Convert grid points to arrays for interpolation
    from scipy.interpolate import griddata

    grid_array = np.array(grid_points)
    pixels = grid_array[:, 0]
    lines = grid_array[:, 1]
    lons = grid_array[:, 2]
    lats = grid_array[:, 3]

    # Use griddata to interpolate
    try:
        pixel = griddata((lons, lats), pixels, (lon, lat), method='linear')
        line = griddata((lons, lats), lines, (lon, lat), method='linear')

        if np.isnan(pixel) or np.isnan(line):
            # Fallback to nearest if linear fails
            pixel = griddata((lons, lats), pixels, (lon, lat), method='nearest')
            line = griddata((lons, lats), lines, (lon, lat), method='nearest')

        return int(pixel), int(line)
    except:
        return None, None


def get_polygon_pixel_bounds(polygon, grid_points, img_width, img_height):
    """Find pixel bounds that contain the polygon using interpolation."""
    minx, miny, maxx, maxy = polygon.bounds

    print(f"  Polygon bounds: lon=[{minx:.6f}, {maxx:.6f}], lat=[{miny:.6f}, {maxy:.6f}]")

    # Get all corners of the polygon bounding box
    corners = [
        (miny, minx),  # Bottom-left (lat, lon)
        (miny, maxx),  # Bottom-right
        (maxy, minx),  # Top-left
        (maxy, maxx),  # Top-right
    ]

    # Interpolate each corner to pixel coordinates
    pixels = []
    lines = []

    for lat, lon in corners:
        pixel, line = interpolate_latlon_to_pixel(lat, lon, grid_points)
        if pixel is not None and line is not None:
            pixels.append(pixel)
            lines.append(line)

    if not pixels:
        print(f"  Failed to interpolate polygon corners to pixels")
        return None

    # Get bounding box of interpolated corners
    min_pixel = max(0, min(pixels))
    max_pixel = min(img_width, max(pixels))
    min_line = max(0, min(lines))
    max_line = min(img_height, max(lines))

    print(f"  Interpolated pixel bounds: pixel=[{min_pixel}, {max_pixel}], line=[{min_line}, {max_line}]")
    print(f"  Region size: {max_pixel - min_pixel} x {max_line - min_line} pixels")

    return (min_pixel, min_line, max_pixel, max_line)


def read_tiff_region_from_zip(zip_path, tiff_file, polygon):
    """Read a specific region from TIFF data in ZIP file using polygon bounds."""
    try:
        # Increase PIL's image size limit
        Image.MAX_IMAGE_PIXELS = None

        # Get geolocation grid
        print("  Reading geolocation grid...")
        grid_points = get_geolocation_grid(zip_path)

        if not grid_points:
            print("  Warning: No geolocation grid found, reading full image")
            # Fallback to reading full image
            with zipfile.ZipFile(zip_path, 'r') as z:
                with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as tmp:
                    tmp.write(z.read(tiff_file))
                    tmp_path = tmp.name

                with rasterio.open(tmp_path) as src:
                    data = src.read(1)

                os.unlink(tmp_path)
                return data

        with zipfile.ZipFile(zip_path, 'r') as z:
            # Extract to temporary file
            with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as tmp:
                tmp.write(z.read(tiff_file))
                tmp_path = tmp.name

            # Open with rasterio to get dimensions
            with rasterio.open(tmp_path) as src:
                img_width = src.width
                img_height = src.height

                print(f"  Image size: {img_width} x {img_height} pixels")

                # Get pixel bounds for polygon
                bounds = get_polygon_pixel_bounds(polygon, grid_points, img_width, img_height)

                if bounds is None:
                    print("  Warning: Polygon not found in image, reading full image")
                    data = src.read(1)
                else:
                    min_pixel, min_line, max_pixel, max_line = bounds
                    width = max_pixel - min_pixel
                    height = max_line - min_line

                    print(f"  Polygon pixel bounds: pixel=[{min_pixel}, {max_pixel}], line=[{min_line}, {max_line}]")
                    print(f"  Extracting region: {width} x {height} pixels")

                    # Read the windowed data
                    from rasterio.windows import Window
                    window = Window(min_pixel, min_line, width, height)
                    data = src.read(1, window=window)

                    print(f"  Successfully extracted region: {data.shape}")

            os.unlink(tmp_path)
            return data
            
    except Exception as e:
        print(f"  Error reading TIFF region: {e}")
        import traceback
        traceback.print_exc()
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


def process_polarization(zip_path, polarization, polygon, output_folder):
    """Process a single polarization for the given polygon."""
    # Find TIFF files for this polarization
    tiff_files = find_tiff_files(zip_path, polarization)
    
    if not tiff_files:
        print(f"  ✗ No {polarization.upper()} data found")
        return False
    
    tiff_file = tiff_files[0]
    print(f"  Reading {polarization.upper()}: {Path(tiff_file).name}")
    
    # Read the region
    data = read_tiff_region_from_zip(zip_path, tiff_file, polygon)

    if data is None or data.size == 0:
        print(f"  ✗ Failed to read data")
        return False
    
    print(f"  Data shape: {data.shape}")
    print(f"  Data range: {data.min():.2f} to {data.max():.2f}")
    
    # Convert to dB (log scale)
    data_db = 10 * np.log10(data + 1e-10)
    
    # Enhance contrast
    print("  Enhancing contrast...")
    data_enhanced = enhance_contrast(data_db, contrast_percentile)
    
    # Convert to 8-bit
    data_8bit = (data_enhanced * 255).astype(np.uint8)
    
    # Create image
    img = Image.fromarray(data_8bit)

    # Generate output filename
    date_str = zip_path.stem.split('_')[4][:8]
    output_name = f"{date_str}_{polarization.upper()}.png"
    output_path = output_folder / output_name
    
    # Save with compression
    print(f"  Saving {polarization.upper()} image...")
    img.save(output_path, 'PNG', optimize=True, compress_level=9)
    
    # Check file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  File size: {file_size_mb:.2f} MB")
    
    # Downsample if too large
    if file_size_mb > max_file_size_mb:
        print(f"  File exceeds {max_file_size_mb} MB, downsampling...")
        scale_factor = np.sqrt(max_file_size_mb / file_size_mb)
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img_resized.save(output_path, 'PNG', optimize=True, compress_level=9)
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Resized to: {new_width}x{new_height}")
        print(f"  New file size: {file_size_mb:.2f} MB")
    
    print(f"  ✓ Saved to: {output_path}")
    return True


def process_all_files():
    """Process all Sentinel-1 files for all polarizations."""
    # Parse polygon
    polygon = parse_wkt_polygon(wkt_aoi)
    print(f"Target polygon bounds: {polygon.bounds}")
    
    # Setup output folders
    output_folders = setup_output_folders()
    print(f"\nOutput folders created:")
    for pol, folder in output_folders.items():
        print(f"  {pol.upper()}: {folder}")
    
    # Find all ZIP files
    input_path = Path(input_folder)
    zip_files = sorted(input_path.glob('S1*.zip'))
    
    if not zip_files:
        print(f"\nNo Sentinel-1 files found in {input_folder}")
        return
    
    print(f"\nFound {len(zip_files)} Sentinel-1 files\n")
    
    # Statistics
    stats = {pol: {'success': 0, 'failed': 0, 'skipped': 0} for pol in polarizations}
    
    for i, zip_file in enumerate(zip_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(zip_files)}] {zip_file.name}")
        print(f"{'='*60}")
        
        for polarization in polarizations:
            output_folder = output_folders[polarization]
            
            # Generate output filename to check if exists
            date_str = zip_file.stem.split('_')[4][:8]
            output_name = f"{date_str}_{polarization.upper()}.png"
            output_path = output_folder / output_name
            
            if output_path.exists():
                print(f"\n{polarization.upper()}: Skipping (already exists)")
                stats[polarization]['skipped'] += 1
                continue
            
            print(f"\nProcessing {polarization.upper()}:")
            success = process_polarization(zip_file, polarization, polygon, output_folder)
            
            if success:
                stats[polarization]['success'] += 1
            else:
                stats[polarization]['failed'] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    
    for pol in polarizations:
        print(f"\n{pol.upper()}:")
        print(f"  ✓ Successfully converted: {stats[pol]['success']}")
        print(f"  → Skipped (already exists): {stats[pol]['skipped']}")
        if stats[pol]['failed'] > 0:
            print(f"  ✗ Failed: {stats[pol]['failed']}")
    
    print(f"\nOutput base folder: {output_base_folder}/")


def main():
    """Main function."""
    print("="*60)
    print("SENTINEL-1 POLYGON EXTRACTOR")
    print("="*60)
    print("\nExtracts data within a polygon region from Sentinel-1 SAR data")
    print("Creates separate PNG files for VV, VH, and HH polarizations\n")
    
    # Check dependencies
    try:
        from shapely import wkt
        import pyproj
        import rasterio
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("\nPlease install required packages:")
        print("  pip install shapely pyproj rasterio")
        return
    
    process_all_files()


if __name__ == '__main__':
    main()
