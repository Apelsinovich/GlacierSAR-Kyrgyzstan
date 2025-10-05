#!/usr/bin/env python3
"""
Direct VV GeoTIFF Downloader for OPERA products
Downloads VV.tif files directly using known product names and URLs
No placeholders needed - just downloads the actual GeoTIFF files
"""

import yaml
import requests
import logging
from pathlib import Path
from tqdm import tqdm

# Load configuration
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

KNOWN_PRODUCTS = [
    # Frame 228503 - Complete glacier coverage (August time series 2016-2025)
    "OPERA_L2_RTC-S1_T107-228503-IW3_20160827T010445Z_20250928T140844Z_S1A_30_v1.0",  # Aug 27, 2016
    "OPERA_L2_RTC-S1_T107-228503-IW3_20170810T010450Z_20250924T152248Z_S1A_30_v1.0",  # Aug 10, 2017  
    "OPERA_L2_RTC-S1_T107-228503-IW3_20180817T010457Z_20250919T052623Z_S1A_30_v1.0",  # Aug 17, 2018
    "OPERA_L2_RTC-S1_T107-228503-IW3_20190824T010503Z_20250913T212350Z_S1A_30_v1.0",  # Aug 24, 2019
    "OPERA_L2_RTC-S1_T107-228503-IW3_20200830T010510Z_20250908T045840Z_S1A_30_v1.0",  # Aug 30, 2020
    "OPERA_L2_RTC-S1_T107-228503-IW3_20210825T010515Z_20250901T013425Z_S1A_30_v1.0",  # Aug 25, 2021
    "OPERA_L2_RTC-S1_T107-228503-IW3_20220820T010522Z_20250216T171154Z_S1A_30_v1.0",  # Aug 20, 2022
    "OPERA_L2_RTC-S1_T107-228503-IW3_20230827T010527Z_20250212T163617Z_S1A_30_v1.0",  # Aug 27, 2023
    "OPERA_L2_RTC-S1_T107-228503-IW3_20240821T010523Z_20240821T064704Z_S1A_30_v1.0",  # Aug 21, 2024
    "OPERA_L2_RTC-S1_T107-228503-IW3_20250828T010514Z_20250828T085403Z_S1A_30_v1.0",  # Aug 28, 2025
]

def download_vv_geotiffs():
    """Download VV GeoTIFF files directly"""
    
    config = load_config()
    tif_dir = Path(config['directories']['satellite_data'])
    tif_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"VV GeoTIFF Downloader")
    print(f"Downloading {len(KNOWN_PRODUCTS)} VV.tif files...")
    print(f"Frame 228503 time series: 2016-2025 (complete glacier coverage)")
    print(f"Additional July products: 2020, 2025")
    print(f"Output directory: {tif_dir}")
    print()
    
    downloaded_count = 0
    
    for product_name in tqdm(KNOWN_PRODUCTS, desc="Downloading VV.tif files"):
        
        # Construct direct URL to VV.tif file
        vv_url = f"https://cumulus.asf.earthdatacloud.nasa.gov/OPERA/OPERA_L2_RTC-S1/{product_name}/{product_name}_VV.tif"
        
        # Output file path
        vv_file = tif_dir / f"{product_name}_VV.tif"
        
        # Skip if already downloaded
        if vv_file.exists():
            downloaded_count += 1
            continue
        
        try:
            # Download with authentication (uses ~/.netrc automatically)
            response = requests.get(vv_url, stream=True, timeout=30)
            
            if response.status_code == 200:
                with open(vv_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                downloaded_count += 1
                
            else:
                print(f"  Failed to download (HTTP {response.status_code}): {product_name}")
                
        except Exception as e:
            print(f"  Download error for {product_name}: {e}")
            continue
    
    print(f"\nSuccessfully downloaded {downloaded_count} VV.tif files!")
    print(f"Files saved in: {tif_dir}")
    print(f"\nNext step: python generate_frames.py")

if __name__ == "__main__":
    download_vv_geotiffs()