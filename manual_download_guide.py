#!/usr/bin/env python3
"""
Manual Download Guide for Sentinel-1 Data
Alternative approach when ASF API is not available
"""

import webbrowser
import time

def open_asf_search():
    """Open ASF search page in browser"""
    print("🌐 Opening ASF search page in your browser...")
    
    # ASF search URL with pre-filled parameters for Golubina Glacier
    url = "https://search.asf.alaska.edu/"
    
    # Try to open in browser
    try:
        webbrowser.open(url)
        print(f"✅ Opened: {url}")
        print("📋 Please follow these steps:")
        print("   1. Wait for the page to load")
        print("   2. Enter coordinates: 42.565, 74.5")
        print("   3. Set filters:")
        print("      - Dataset: Sentinel-1")
        print("      - Beam Mode: IW")
        print("      - Polarization: VV+VH")
        print("      - Product Type: GRD_HD")
        print("      - Date range: 2023-06-01 to 2023-08-31")
        print("   4. Click Search")
        print("   5. Select 1-2 recent images")
        print("   6. Click Download button")
        print("   7. Save files to output/raw_data/")
        
    except Exception as e:
        print(f"❌ Could not open browser: {e}")
        print(f"💡 Please manually visit: {url}")

def show_download_instructions():
    """Show detailed download instructions"""
    print("\n" + "=" * 60)
    print("📥 MANUAL DOWNLOAD INSTRUCTIONS")
    print("=" * 60)
    
    instructions = """
🎯 STEP-BY-STEP DOWNLOAD GUIDE:

1️⃣  OPEN ASF SEARCH:
   https://search.asf.alaska.edu/

2️⃣  SET SEARCH PARAMETERS:
   • Location: Enter "42.565, 74.5" or draw a box around Ala-Archa
   • Dataset: Sentinel-1
   • Beam Mode: IW (Interferometric Wide)
   • Polarization: VV+VH (or VV if VH not available)
   • Product Type: GRD_HD (Ground Range Detected, High resolution)
   • Processing Level: Leave default

3️⃣  SET DATE RANGE:
   For testing: 2023-06-01 to 2023-08-31 (summer season)
   For full study: 2015-01-01 to 2025-12-31

4️⃣  SEARCH AND SELECT:
   • Click "Search" button
   • Wait for results to load
   • Sort by "Start Time" (newest first)
   • Select 1-2 recent images (checkboxes)
   • Look for files ~800-900 MB in size

5️⃣  DOWNLOAD:
   • Click "Download" button
   • Choose "Download Selected Products"
   • Files will be downloaded as .zip archives
   • Save to: output/raw_data/

6️⃣  EXTRACT (if needed):
   • Unzip the downloaded files
   • You should see .tif files inside

7️⃣  READY FOR PROCESSING:
   • Run: python3 time_series_processor.py
   • Or: python3 example_workflow.py

================================================================================

🗂️  EXPECTED FILES:
• S1A_IW_GRDH_1SDV_20230715T..._VV_VH.zip (~850 MB)
• S1B_IW_GRDH_1SDV_20230703T..._VV_VH.zip (~850 MB)

📊 FILE SIZE GUIDE:
• Sentinel-1 GRD: ~800-900 MB per file
• Processing time: ~2-3 minutes per file
• Storage needed: ~10 GB for 10+ years of data

================================================================================

💡 TIPS:
• Use VV+VH polarization for best classification results
• Download from summer months (June-August) for melt analysis
• Start with 2-3 recent files for testing
• ASF is free for scientific use

================================================================================

🚨 COMMON ISSUES:
• "No results found": Try wider date range or larger area
• "Download failed": Check internet connection, try VPN
• "Large files": Normal for SAR data, ~850 MB per scene

================================================================================
"""
    print(instructions)

def test_local_files():
    """Check for existing SAR files in the project"""
    print("\n🔍 Checking for existing SAR files...")
    
    import os
    from pathlib import Path
    
    raw_data_dir = Path("output/raw_data")
    
    if not raw_data_dir.exists():
        print("❌ output/raw_data/ directory not found")
        print("💡 Create it: mkdir -p output/raw_data")
        return False
    
    # Look for SAR files
    sar_files = []
    sar_files.extend(raw_data_dir.glob("*.zip"))
    sar_files.extend(raw_data_dir.glob("*.tif"))
    
    s1_files = []
    for file_path in sar_files:
        filename = file_path.name.upper()
        if 'S1' in filename and ('VV' in filename or 'VH' in filename):
            s1_files.append(file_path)
    
    if s1_files:
        print(f"✅ Found {len(s1_files)} Sentinel-1 files:")
        for file_path in s1_files[:5]:  # Show first 5
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"   • {file_path.name} ({size_mb:.1f} MB)")
        
        if len(s1_files) > 5:
            print(f"   ... and {len(s1_files) - 5} more files")
        
        print("🚀 Ready for processing!")
        return True
    else:
        print("❌ No Sentinel-1 files found")
        print("💡 Follow the manual download instructions above")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🌐 MANUAL DOWNLOAD GUIDE")
    print("Alternative when ASF API is not available")
    print("=" * 60)
    
    # Try to open ASF search
    open_asf_search()
    
    # Show instructions
    show_download_instructions()
    
    # Check for existing files
    has_files = test_local_files()
    
    if has_files:
        print("✅ You have SAR files ready for processing!")
        print("🚀 Next step: python3 time_series_processor.py")
    else:
        print("📥 Please download SAR files using the instructions above")
        print("🚀 After downloading: python3 time_series_processor.py")
    
    print("=" * 60)
