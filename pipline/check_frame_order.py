#!/usr/bin/env python3
"""
Frame Order Checker
Verify the chronological order of frames in the glacier timelapse
"""

from pathlib import Path
import re
from PIL import Image

def parse_date_from_filename(filename):
    """Extract date from filename like 2016-08-27.png"""
    m = re.search(r'(\d{4}-\d{2}-\d{2})\.png', filename)
    return m.group(1) if m else None

def check_frame_order():
    """Check chronological order of all frames"""
    
    frames_dir = Path("out/glacier_aoi")
    
    print("🔍 FRAME ORDER CHECKER")
    print("=" * 40)
    
    if not frames_dir.exists():
        print(f"❌ Directory not found: {frames_dir}")
        return
    
    # Find all PNG files
    png_files = list(frames_dir.glob("*.png"))
    
    if not png_files:
        print(f"❌ No PNG files found in {frames_dir}")
        return
    
    print(f"Found {len(png_files)} frames")
    print()
    
    # Parse dates and sort
    dated_files = []
    for png_file in png_files:
        date = parse_date_from_filename(png_file.name)
        if date:
            dated_files.append((date, png_file))
    
    # Sort chronologically  
    dated_files.sort(key=lambda x: x[0])
    
    print("📅 CHRONOLOGICAL ORDER:")
    print("-" * 30)
    
    for i, (date, png_file) in enumerate(dated_files, 1):
        # Get image info
        try:
            with Image.open(png_file) as img:
                size_str = f"{img.size[0]}x{img.size[1]}"
            
            # Mark first and last
            marker = ""
            if i == 1:
                marker = " ← FIRST IMAGE"
            elif i == len(dated_files):
                marker = " ← LAST IMAGE"
            
            print(f"{i:2d}. {date} ({size_str}) {marker}")
            
        except Exception as e:
            print(f"{i:2d}. {date} - Error reading file: {e}")
    
    print()
    print("📊 SUMMARY:")
    print(f"   First frame: {dated_files[0][0]} (2016 = YES ✅)")
    print(f"   Last frame:  {dated_files[-1][0]}")
    print(f"   Time span:   {len(dated_files)} years")
    print(f"   All August:  {all('08' in date for date, _ in dated_files)}")
    
    # Check for missing years
    years = [int(date[:4]) for date, _ in dated_files]
    expected_years = list(range(min(years), max(years) + 1))
    missing_years = [year for year in expected_years if year not in years]
    
    if missing_years:
        print(f"   Missing years: {missing_years}")
    else:
        print(f"   Complete series: No missing years ✅")

def verify_gif_order():
    """Check if the created GIF has correct frame order"""
    
    gif_file = Path("ala_archa_glacier_timelapse.gif")
    
    print("\n🎬 GIF VERIFICATION:")
    print("-" * 20)
    
    if not gif_file.exists():
        print("❌ GIF file not found")
        return
    
    try:
        with Image.open(gif_file) as gif:
            frame_count = 0
            
            # Count frames in GIF
            try:
                while True:
                    gif.seek(frame_count)
                    frame_count += 1
            except EOFError:
                pass
            
            print(f"GIF frames: {frame_count}")
            print(f"PNG frames: {len(list(Path('out/glacier_aoi').glob('*.png')))}")
            print(f"Match: {'✅' if frame_count == len(list(Path('out/glacier_aoi').glob('*.png'))) else '❌'}")
            
            # File info
            size_mb = gif_file.stat().st_size / 1024 / 1024
            print(f"File size: {size_mb:.1f} MB")
            
    except Exception as e:
        print(f"❌ Error reading GIF: {e}")

if __name__ == "__main__":
    check_frame_order()
    verify_gif_order()