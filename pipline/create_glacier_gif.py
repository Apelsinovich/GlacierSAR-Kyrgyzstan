#!/usr/bin/env python3
"""
GIF Creator from Cropped Glacier Images
Creates animated GIF from PNG frames showing glacier changes over time
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import re

def parse_year_from_filename(filename):
    """Extract year from filename - just get the first 4 digits"""
    m = re.search(r'(\d{4})', filename)
    return int(m.group(1)) if m else None

def add_year_label(image, year):
    """Add year label to the top-left corner of the image"""
    # Create a copy of the image to avoid modifying the original
    img_with_label = image.copy()
    draw = ImageDraw.Draw(img_with_label)
    
    # Try to use a smaller font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        try:
            font = ImageFont.truetype("Arial.ttf", 24)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
    
    year_text = str(year)
    
    # Calculate text size
    if font:
        bbox = draw.textbbox((0, 0), year_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        # Fallback for default font
        text_width = len(year_text) * 8
        text_height = 12
    
    # Position in top-left corner with some padding
    padding = 10
    x = padding
    y = padding
    
    # Draw background rectangle for better visibility
    bg_padding = 5
    bg_coords = [
        x - bg_padding,
        y - bg_padding,
        x + text_width + bg_padding,
        y + text_height + bg_padding
    ]
    
    # Semi-transparent background
    draw.rectangle(bg_coords, fill=(0, 0, 0, 180))
    
    # Draw the year text in white
    draw.text((x, y), year_text, fill=(255, 255, 255), font=font)
    
    return img_with_label

def create_glacier_gif():
    """Create animated GIF from cropped glacier images ordered by year"""
    
    # Use the pure 6-level images collection directory
    frames_dir = Path("out/db_distribution_analysis/pure_6level_images_collection")
    output_gif = Path("ala_archa_glacier_timelapse_6level.gif")
    
    # Also check alternative directories if the first doesn't exist
    if not frames_dir.exists():
        frames_dir = Path("out/glacier_aoi")
        output_gif = Path("ala_archa_glacier_timelapse.gif")
    
    if not frames_dir.exists():
        frames_dir = Path("out/glacier_cropped_from_frame_pngs")
        output_gif = Path("ala_archa_glacier_timelapse_raw.gif")
    
    if not frames_dir.exists():
        print(f"Directory not found. Tried:")
        print(f"   - out/db_distribution_analysis/pure_6level_images_collection")
        print(f"   - out/glacier_aoi")
        print(f"   - out/glacier_cropped_from_frame_pngs")
        return
    
    # Find all PNG files
    png_files = list(frames_dir.glob("*.png"))
    
    if not png_files:
        print(f"No PNG files found in {frames_dir}")
        return
    
    print(f"Found {len(png_files)} PNG frames in {frames_dir}")
    
    # Parse years and sort chronologically
    year_files = []
    for png_file in png_files:
        year = parse_year_from_filename(png_file.name)
        if year and year <= 2025:  # Only include years up to 2025
            year_files.append((year, png_file))
    
    # Sort chronologically by year
    year_files.sort(key=lambda x: x[0])
    
    if not year_files:
        print("No valid year files found")
        return
    
    print(f"Year range: {year_files[0][0]} to {year_files[-1][0]}")
    
    # Load images and add year labels
    frames = []
    for year, png_file in year_files:
        try:
            img = Image.open(png_file)
            # Convert to RGB if needed (for better GIF compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Add year label to the image
            img_with_year = add_year_label(img, year)
            frames.append(img_with_year)
            
            print(f"  Loaded: {year} ({img.size[0]}x{img.size[1]}) - {png_file.name}")
        except Exception as e:
            print(f"  Failed to load {png_file.name}: {e}")
    
    if not frames:
        print("No valid frames loaded")
        return
    
    # Create GIF
    print(f"\nCreating GIF with year labels...")
    print(f"   Frames: {len(frames)}")
    print(f"   Duration: 1000ms per frame")
    print(f"   Output: {output_gif}")
    
    try:
        frames[0].save(
            output_gif,
            save_all=True,
            append_images=frames[1:],
            duration=1000,  # 1 second per frame
            loop=0  # infinite loop
        )
        
        # Get file size
        size_mb = output_gif.stat().st_size / 1024 / 1024
        
        print(f"\nGIF created successfully!")
        print(f"File: {output_gif}")
        print(f"Size: {size_mb:.1f} MB")
        print(f"Shows glacier changes from {year_files[0][0]} to {year_files[-1][0]}")
        
        # Also create a faster version
        fast_gif = Path(f"ala_archa_glacier_fast_{len(frames)}frames.gif")
        frames[0].save(
            fast_gif,
            save_all=True,
            append_images=frames[1:],
            duration=500,  # faster - 500ms per frame
            loop=0
        )
        
        print(f"\nAlso created fast version: {fast_gif}")
        
        # Create a slow detailed version for analysis
        detailed_gif = Path(f"ala_archa_glacier_detailed_{len(frames)}frames.gif")
        frames[0].save(
            detailed_gif,
            save_all=True,
            append_images=frames[1:],
            duration=1500,  # slower - 1.5 seconds per frame
            loop=0
        )
        
        print(f"Also created detailed version: {detailed_gif}")
        
    except Exception as e:
        print(f"Error creating GIF: {e}")

def create_mp4_with_ffmpeg():
    """Alternative: Create MP4 video using FFmpeg"""
    
    frames_dir = Path("out/db_distribution_analysis/pure_6level_images_collection")
    
    if not frames_dir.exists():
        frames_dir = Path("out/glacier_aoi")
    
    if not frames_dir.exists():
        frames_dir = Path("out/glacier_cropped_from_frame_pngs")
    
    print(f"\nAlternative: Create MP4 with FFmpeg:")
    print(f"cd {frames_dir.parent}")
    print(f"ffmpeg -framerate 1 -pattern_type glob -i '{frames_dir.name}/*.png' \\")
    print(f"  -c:v libx264 -pix_fmt yuv420p -crf 18 \\")
    print(f"  ala_archa_glacier_timelapse.mp4")
    print(f"\nFor faster playback:")
    print(f"ffmpeg -framerate 2 -pattern_type glob -i '{frames_dir.name}/*.png' \\")
    print(f"  -c:v libx264 -pix_fmt yuv420p -crf 18 \\")
    print(f"  ala_archa_glacier_timelapse_fast.mp4")

if __name__ == "__main__":
    print("Ala Archa Glacier Timelapse Creator")
    print("=" * 50)
    
    create_glacier_gif()
    create_mp4_with_ffmpeg()