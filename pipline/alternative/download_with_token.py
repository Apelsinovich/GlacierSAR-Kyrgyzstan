#!/usr/bin/env python3
"""
Downloading SAR images using Bearer token
"""

import asf_search as asf
from datetime import datetime
import yaml
from pathlib import Path
import sys
import os


def download_with_bearer_token(bearer_token, start_year=2017, end_year=2025, max_downloads=9):
    """Download using Bearer token"""
    
    print("=" * 80)
    print("🏔️  DOWNLOADING GOLUBINA GLACIER IMAGES WITH TOKEN")
    print("=" * 80)
    
    # Load configuration
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Get glacier coordinates
    bbox_config = config['sar_data']['api_download']['target_glacier_bbox']
    
    # Search parameters
    wkt_aoi = f"POLYGON(({bbox_config['min_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['min_lat']}))"
    
    print(f"📍 Area: Golubina Glacier, Ala-Archa")
    print(f"   Coordinates: {bbox_config['min_lon']}, {bbox_config['min_lat']} - "
          f"{bbox_config['max_lon']}, {bbox_config['max_lat']}")
    
    # Directory for saving
    output_dir = Path("output/raw_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Directory: {output_dir}")
    
    target_month = config['sar_data']['api_download']['target_month']
    
    print(f"\n⏰ Period: {start_year} - {end_year}")
    print(f"📅 Month: {target_month} (July - peak melting)")
    print(f"🛰️  Satellite: Sentinel-1A")
    print(f"📡 Polarization: VV+VH")
    print(f"🎯 Maximum: {max_downloads} images")
    
    all_results = []
    
    # Search by years
    print("\n🔍 Searching for available images...")
    for year in range(start_year, end_year + 1):
        if len(all_results) >= max_downloads:
            print(f"✋ Reached limit ({max_downloads}), stopping search")
            break
            
        start_date = f"{year}-{target_month-1:02d}-01" if target_month > 1 else f"{year}-01-01"
        end_date = f"{year}-{target_month+1:02d}-30" if target_month < 12 else f"{year}-12-31"
        
        try:
            results = asf.geo_search(
                platform=[asf.PLATFORM.SENTINEL1],
                intersectsWith=wkt_aoi,
                start=start_date,
                end=end_date,
                processingLevel=[asf.PRODUCT_TYPE.GRD_HD],
                beamMode=[asf.BEAMMODE.IW],
            )
            
            if results:
                target_date = datetime(year, target_month, 15)
                best_result = None
                min_diff = float('inf')
                
                for r in results:
                    scene_date_str = r.properties['startTime']
                    if isinstance(scene_date_str, str):
                        scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
                    else:
                        scene_date = scene_date_str
                    
                    diff = abs((scene_date.replace(tzinfo=None) - target_date).days)
                    if diff < min_diff:
                        min_diff = diff
                        best_result = r
                
                if best_result:
                    all_results.append(best_result)
                    scene_date_str = best_result.properties['startTime']
                    if isinstance(scene_date_str, str):
                        scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
                    else:
                        scene_date = scene_date_str
                    scene_date_formatted = scene_date.strftime('%Y-%m-%d')
                    file_size = best_result.properties.get('bytes', 0) / (1024**3)
                    print(f"✅ {year}: found image from {scene_date_formatted} (~{file_size:.2f} GB)")
            else:
                print(f"❌ {year}: no images found")
                
        except Exception as e:
            print(f"❌ {year}: search error - {e}")
    
    if not all_results:
        print("\n❌ No available images found!")
        return []
    
    print(f"\n📊 Total found: {len(all_results)} images")
    
    # Show details
    print("\n📋 Details of found images:")
    print("-" * 80)
    for i, result in enumerate(all_results, 1):
        props = result.properties
        scene_date_str = props['startTime']
        if isinstance(scene_date_str, str):
            scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
        else:
            scene_date = scene_date_str
        print(f"{i}. Date: {scene_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Satellite: {props['platform']}")
        print(f"   Size: {props.get('bytes', 0)/(1024**3):.2f} GB")
        print(f"   File: {props['fileName']}")
        print()
    
    total_size = sum(r.properties.get('bytes', 0) for r in all_results) / (1024**3)
    print(f"💾 Total size: {total_size:.2f} GB")
    print(f"⏱️  Estimated time: {total_size*2:.0f}-{total_size*5:.0f} minutes")
    
    print("\n📥 Starting download with Bearer token...")
    
    # Create session with Bearer token
    session = asf.ASFSession()
    session.auth_with_token(bearer_token)
    
    downloaded_count = 0
    failed_files = []
    
    try:
        for i, result in enumerate(all_results, 1):
            filename = result.properties['fileName']
            output_path = output_dir / filename
            
            print(f"\n[{i}/{len(all_results)}] Downloading: {filename}")
            
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024**2)
                print(f"   ⏭️  File already exists ({file_size_mb:.1f} MB), skipping")
                downloaded_count += 1
                continue
            
            try:
                print(f"   ⬇️  Starting download...")
                result.download(path=str(output_dir), session=session)
                
                if output_path.exists():
                    file_size_mb = output_path.stat().st_size / (1024**2)
                    print(f"   ✅ Downloaded successfully ({file_size_mb:.1f} MB)")
                    downloaded_count += 1
                else:
                    print(f"   ⚠️  File not found after download")
                    failed_files.append(filename)
                    
            except Exception as e:
                print(f"   ❌ Download error: {e}")
                failed_files.append(filename)
        
        print("\n" + "=" * 80)
        print("✅ DOWNLOAD COMPLETED")
        print("=" * 80)
        print(f"📊 Successful: {downloaded_count}/{len(all_results)} files")
        
        if failed_files:
            print(f"\n⚠️  Failed to download {len(failed_files)} files:")
            for fname in failed_files:
                print(f"   • {fname}")
        
        print(f"\n📁 Files saved to: {output_dir}")
        print("🚀 Ready for processing!")
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
    
    return all_results


if __name__ == "__main__":
    # Get token from command line argument or environment variable
    bearer_token = None
    
    if len(sys.argv) > 1:
        bearer_token = sys.argv[1]
    elif 'EARTHDATA_TOKEN' in os.environ:
        bearer_token = os.environ['EARTHDATA_TOKEN']
    else:
        print("❌ Error: Bearer token not provided!")
        print("\nUsage:")
        print("  Option 1: python3 download_with_token.py YOUR_TOKEN")
        print("  Option 2: export EARTHDATA_TOKEN='YOUR_TOKEN' && python3 download_with_token.py")
        sys.exit(1)
    
    print("🔐 Bearer token received")
    
    try:
        results = download_with_bearer_token(
            bearer_token=bearer_token,
            start_year=2017,
            end_year=2025,
            max_downloads=9
        )
        
        if results:
            print(f"\n✅ Operation completed! Found and processed {len(results)} images.")
        else:
            print("\n⚠️  No images found.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


