#!/usr/bin/env python3
"""
Script for downloading Golubina Glacier images via ASF API
Uses official asf_search library
"""

import asf_search as asf
from datetime import datetime
import yaml
from pathlib import Path


def download_glacier_images():
    """Download SAR images of Golubina Glacier"""
    
    print("=" * 80)
    print("🏔️  DOWNLOADING GOLUBINA GLACIER IMAGES")
    print("=" * 80)
    
    # Load configuration
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Get glacier coordinates from config
    bbox_config = config['sar_data']['api_download']['target_glacier_bbox']
    
    # Search parameters
    wkt_aoi = f"POLYGON(({bbox_config['min_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['min_lat']}))"
    
    print(f"📍 Area of interest: Golubina Glacier, Ala-Archa")
    print(f"   Coordinates: {bbox_config['min_lon']}, {bbox_config['min_lat']} - "
          f"{bbox_config['max_lon']}, {bbox_config['max_lat']}")
    
    # Directory for saving
    output_dir = Path("output/raw_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Directory for saving: {output_dir}")
    
    # Search parameters
    start_year = config['sar_data']['api_download']['start_year']
    end_year = config['sar_data']['api_download']['end_year']
    target_month = config['sar_data']['api_download']['target_month']
    
    print(f"\n⏰ Time period: {start_year} - {end_year}")
    print(f"📅 Target month: {target_month} (July - peak melting)")
    print(f"🛰️  Satellite: Sentinel-1")
    print(f"📡 Polarization: VV+VH (dual-pol)")
    
    all_results = []
    
    # Search by years
    print("\n🔍 Searching for available images...")
    for year in range(start_year, end_year + 1):
        # Extended search period (month ±1)
        start_date = f"{year}-{target_month-1:02d}-01" if target_month > 1 else f"{year}-01-01"
        end_date = f"{year}-{target_month+1:02d}-30" if target_month < 12 else f"{year}-12-31"
        
        try:
            # Search via ASF
            results = asf.geo_search(
                platform=[asf.PLATFORM.SENTINEL1],
                intersectsWith=wkt_aoi,
                start=start_date,
                end=end_date,
                processingLevel=[asf.PRODUCT_TYPE.GRD_HD],
                beamMode=[asf.BEAMMODE.IW],
            )
            
            if results:
                # Filter by month and select best image
                target_date = datetime(year, target_month, 15)
                best_result = None
                min_diff = float('inf')
                
                for r in results:
                    scene_date_str = r.properties['startTime']
                    # Convert string to datetime
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
                    file_size = best_result.properties.get('bytes', 0) / (1024**3)  # GB
                    print(f"✅ {year}: found image from {scene_date_formatted} "
                          f"(~{file_size:.2f} GB)")
            else:
                print(f"❌ {year}: no images found")
                
        except Exception as e:
            print(f"❌ {year}: search error - {e}")
    
    if not all_results:
        print("\n❌ No available images found!")
        print("💡 Try expanding the time range or changing the search area")
        return
    
    print(f"\n📊 Total images found: {len(all_results)}")
    
    # Show details of found images
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
        print(f"   Mode: {props['beamModeType']}")
        print(f"   Polarization: {props.get('polarization', 'N/A')}")
        print(f"   Size: {props.get('bytes', 0)/(1024**3):.2f} GB")
        print(f"   File name: {props['fileName']}")
        print()
    
    # Ask about downloading
    total_size = sum(r.properties.get('bytes', 0) for r in all_results) / (1024**3)
    print(f"💾 Total size for download: {total_size:.2f} GB")
    print(f"⏱️  Estimated download time: {total_size*2:.0f}-{total_size*5:.0f} minutes")
    
    response = input("\n❓ Start download? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y', 'да', 'д']:
        print("\n📥 Starting download...")
        print("⚠️  IMPORTANT: NASA Earthdata credentials required for download")
        print("   Registration: https://urs.earthdata.nasa.gov/users/new")
        print()
        
        # Attempt download
        session = asf.ASFSession()
        
        try:
            # Download each file
            for i, result in enumerate(all_results, 1):
                filename = result.properties['fileName']
                output_path = output_dir / filename
                
                print(f"\n[{i}/{len(all_results)}] Downloading: {filename}")
                
                if output_path.exists():
                    print(f"   ⏭️  File already exists, skipping")
                    continue
                
                try:
                    result.download(path=str(output_dir), session=session)
                    print(f"   ✅ Downloaded successfully")
                except Exception as e:
                    print(f"   ❌ Download error: {e}")
            
            print("\n" + "=" * 80)
            print("✅ DOWNLOAD COMPLETED")
            print("=" * 80)
            print(f"📁 Files saved to: {output_dir}")
            print("🚀 Ready for processing in pipeline!")
            
        except Exception as e:
            print(f"\n❌ Error during download: {e}")
            print("\n💡 Possible solutions:")
            print("   1. Register at https://urs.earthdata.nasa.gov")
            print("   2. Configure credentials: asf_search.ASFSession().auth_with_creds()")
            print("   3. Use manual download via https://search.asf.alaska.edu")
    else:
        print("\n📝 Download cancelled")
        print("💡 You can download files manually via:")
        print("   https://search.asf.alaska.edu")
        print("\n📋 List of files for manual download:")
        for result in all_results:
            print(f"   • {result.properties['fileName']}")


if __name__ == "__main__":
    try:
        download_glacier_images()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

