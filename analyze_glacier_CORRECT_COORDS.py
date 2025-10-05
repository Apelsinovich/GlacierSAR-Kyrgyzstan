#!/usr/bin/env python3
"""
CORRECT analysis of Golubina Glacier with precise coordinates
Uses geolocation grid from XML for accurate coordinate conversion
"""

import numpy as np
import rasterio
import rasterio.transform
from datetime import datetime
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from scipy.ndimage import median_filter

print("=" * 80)
print("🏔️  CORRECT ANALYSIS WITH PRECISE COORDINATES")
print("    Method: Geolocation grid from XML + 33.3% percentile")
print("=" * 80)

TARGET_LON = (74.460, 74.520)
TARGET_LAT = (42.440, 42.500)
CALIB_FACTOR = 52.7
GLACIER_PERCENTILE = 33.3

print(f"\n🎯 TARGET AREA:")
print(f"   Lon: {TARGET_LON[0]} - {TARGET_LON[1]}°E")
print(f"   Lat: {TARGET_LAT[0]} - {TARGET_LAT[1]}°N\n")

def get_geolocation_grid(xml_path):
    """Extracts geolocation grid from XML metadata"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Search for geolocationGrid
        ns = {'s1': 'http://www.esa.int/safe/sentinel-1.0'}
        
        geolocation_grid = root.find('.//s1:geolocationGrid', ns)
        if geolocation_grid is None:
            # Try without namespace
            geolocation_grid = root.find('.//geolocationGrid')
        
        if geolocation_grid is None:
            return None
        
        gcps = []
        
        # Search for all geolocationGridPoint
        for point in geolocation_grid.findall('.//geolocationGridPoint'):
            try:
                pixel = int(point.find('pixel').text)
                line = int(point.find('line').text)
                lat = float(point.find('latitude').text)
                lon = float(point.find('longitude').text)
                
                gcps.append(rasterio.control.GroundControlPoint(
                    row=line, col=pixel, x=lon, y=lat
                ))
            except (AttributeError, ValueError, TypeError):
                continue
        
        if not gcps:
            return None
            
        return gcps
        
    except Exception as e:
        print(f"     ⚠️  XML parsing error: {e}")
        return None

def lonlat_to_pixel_precise(lon, lat, gcps, img_width, img_height):
    """Precise conversion of lon/lat to pixel using GCP"""
    try:
        # Create transform from GCPs
        transform = rasterio.transform.from_gcps(gcps)
        
        # Convert lon/lat to pixel
        row, col = rasterio.transform.rowcol(transform, lon, lat)
        
        # Limit to image bounds
        col = int(np.clip(col, 0, img_width - 1))
        row = int(np.clip(row, 0, img_height - 1))
        
        return col, row
        
    except Exception as e:
        return None, None

def calibrate_to_sigma0(data, factor):
    return 10 * np.log10((data.astype(float) ** 2) + 1e-10) - factor

def find_glacier_simple(data_db, percentile=33.3):
    data_filtered = median_filter(data_db, size=3)
    valid = np.isfinite(data_filtered)
    threshold = np.percentile(data_filtered[valid], percentile)
    glacier_mask = (data_filtered <= threshold) & valid
    glacier_pixels = np.sum(glacier_mask)
    return glacier_mask, glacier_pixels, threshold

data_dir = Path("output/raw_data")
safe_dirs = sorted(list(data_dir.glob("*.SAFE")))
vv_files = sorted(list(data_dir.glob("**/*vv*.tiff")))

print(f"📊 Files for analysis: {len(vv_files)}\n")

results = []
failed_years = []

for idx, (safe_dir, vv_file) in enumerate(zip(safe_dirs, vv_files), 1):
    date_str = vv_file.stem.split('-')[4][:8]
    date = datetime.strptime(date_str, '%Y%m%d')
    year = date.year
    
    print(f"[{idx}/{len(vv_files)}] {year}: {date.strftime('%Y-%m-%d')}", end='')
    
    try:
        # Find XML file with geolocation
        xml_files = list(safe_dir.glob("**/s1*vv*.xml"))
        if not xml_files:
            print(" ❌ XML not found")
            failed_years.append(year)
            continue
        
        xml_path = xml_files[0]
        gcps = get_geolocation_grid(xml_path)
        
        if not gcps or len(gcps) < 4:
            print(" ❌ GCP not found in XML")
            failed_years.append(year)
            continue
        
        with rasterio.open(vv_file) as src:
            img_width = src.width
            img_height = src.height
            
            # Convert target area corners to pixels
            corners_lonlat = [
                (TARGET_LON[0], TARGET_LAT[0]),  # SW
                (TARGET_LON[1], TARGET_LAT[0]),  # SE
                (TARGET_LON[1], TARGET_LAT[1]),  # NE
                (TARGET_LON[0], TARGET_LAT[1])   # NW
            ]
            
            pixels_x = []
            pixels_y = []
            
            for lon, lat in corners_lonlat:
                px, py = lonlat_to_pixel_precise(lon, lat, gcps, img_width, img_height)
                if px is None or py is None:
                    raise ValueError("Не удалось конвертировать координаты")
                pixels_x.append(px)
                pixels_y.append(py)
            
            # Define bbox in pixels
            pixel_min = max(0, min(pixels_x))
            pixel_max = min(img_width, max(pixels_x))
            line_min = max(0, min(pixels_y))
            line_max = min(img_height, max(pixels_y))
            
            # Check that area is valid
            if pixel_max <= pixel_min or line_max <= line_min:
                print(f" ❌ Target area outside image")
                failed_years.append(year)
                continue
            
            # Read data
            window_width = pixel_max - pixel_min
            window_height = line_max - line_min
            
            if window_width < 50 or window_height < 50:
                print(f" ❌ Window too small: {window_width}x{window_height}")
                failed_years.append(year)
                continue
            
            region_data = src.read(1, window=((line_min, line_max), (pixel_min, pixel_max)))
            region_db = calibrate_to_sigma0(region_data, CALIB_FACTOR)
            
            glacier_mask, glacier_pixels, threshold = find_glacier_simple(
                region_db, GLACIER_PERCENTILE
            )
            
            glacier_area_km2 = (glacier_pixels * 100) / 1e6
            
            glacier_backscatter = region_db[glacier_mask]
            glacier_backscatter = glacier_backscatter[np.isfinite(glacier_backscatter)]
            
            valid = np.isfinite(region_db)
            total_pixels = np.sum(valid)
            coverage_pct = (glacier_pixels / total_pixels) * 100
            
            stats = {
                'year': year,
                'date': date.strftime('%Y-%m-%d'),
                'glacier_area_km2': float(glacier_area_km2),
                'glacier_pixels': int(glacier_pixels),
                'coverage_percent': float(coverage_pct),
                'mean_backscatter': float(np.mean(glacier_backscatter)),
                'median_backscatter': float(np.median(glacier_backscatter)),
                'std_backscatter': float(np.std(glacier_backscatter)),
                'min_backscatter': float(np.min(glacier_backscatter)),
                'max_backscatter': float(np.max(glacier_backscatter)),
                'threshold_db': float(threshold),
                'window_size': f"{window_width}x{window_height}",
                'gcps_count': len(gcps)
            }
            
            results.append(stats)
            
            print(f" → {glacier_area_km2:>5.2f} km² ({coverage_pct:.1f}%, window: {window_width}x{window_height} px)")
            
    except Exception as e:
        print(f" ❌ Error: {e}")
        failed_years.append(year)

if results:
    output_file = Path("output/results/glacier_golubina_PRECISE.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"📊 RESULTS WITH PRECISE COORDINATES")
    print(f"{'=' * 80}")
    
    print(f"\n{'Year':<6} {'Date':<12} {'Area':<15} {'%':<8} {'Sigma0':<15} {'Window':<15} {'Change from 2017'}")
    print(f"{'-'*6} {'-'*12} {'-'*15} {'-'*8} {'-'*15} {'-'*15} {'-'*18}")
    
    base_area = results[0]['glacier_area_km2']
    
    for r in results:
        change = r['glacier_area_km2'] - base_area
        change_pct = (change / base_area) * 100
        
        if change_pct > 5:
            trend = "🟢"
        elif change_pct < -5:
            trend = "🔴"
        else:
            trend = "✅"
        
        print(f"{r['year']:<6} {r['date']:<12} {r['glacier_area_km2']:>9.2f} km²   {r['coverage_percent']:>5.1f}%  "
              f"{r['mean_backscatter']:>6.2f} dB  {r['window_size']:<15} {trend} {change:+6.2f} ({change_pct:+5.1f}%)")
    
    first = results[0]
    last = results[-1]
    
    area_change = last['glacier_area_km2'] - first['glacier_area_km2']
    area_change_pct = (area_change / first['glacier_area_km2']) * 100
    
    print(f"\n{'=' * 80}")
    print(f"📈 CHANGES {first['year']} → {last['year']} ({len(results)} images)")
    print(f"{'=' * 80}")
    
    print(f"\n❄️  GLACIER AREA:")
    print(f"   {first['year']}: {first['glacier_area_km2']:.2f} km² ({first['coverage_percent']:.1f}%)")
    print(f"   {last['year']}: {last['glacier_area_km2']:.2f} km² ({last['coverage_percent']:.1f}%)")
    print(f"   Change: {area_change:+.2f} km² ({area_change_pct:+.1f}%)")
    
    if abs(area_change_pct) < 10:
        status = "✅ STABLE"
    elif area_change_pct < -10:
        status = "🔴 SHRINKING"
    else:
        status = "🟢 GROWING"
    
    print(f"   Status: {status}")
    
    avg_area = np.mean([r['glacier_area_km2'] for r in results])
    std_area = np.std([r['glacier_area_km2'] for r in results])
    
    print(f"\n🔄 STATISTICS:")
    print(f"   Average: {avg_area:.2f} ± {std_area:.2f} km²")
    print(f"   CV: {(std_area/avg_area)*100:.1f}%")
    
    print(f"\n💾 Results: {output_file}")
    
    if failed_years:
        print(f"\n⚠️  Skipped years: {', '.join(map(str, failed_years))}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ ANALYSIS WITH PRECISE COORDINATES COMPLETED")
    print(f"{'=' * 80}\n")
else:
    print("\n❌ Failed to analyze any images")


