#!/usr/bin/env python3
"""
Example: Using ASF API to download Sentinel-1 data for Golubina Glacier

This script demonstrates how to use the ASF API downloader to get
Sentinel-1 data for the Golubina Glacier in Ala-Archa gorge over multiple years.
"""

from asf_api_downloader import ASFAPIDownloader
import yaml


def example_api_download():
    """Example of downloading Sentinel-1 data via ASF API"""

    print("=" * 80)
    print("🔽 ASF API DOWNLOAD EXAMPLE")
    print("=" * 80)
    print("Downloading Sentinel-1 data for Golubina Glacier")
    print("Target: Ala-Archa Gorge, Kyrgyzstan")
    print("Time period: 2015-2025 (July each year)")
    print("=" * 80)

    # Load configuration
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize downloader
    downloader = ASFAPIDownloader()

    # Get bounding box for Golubina Glacier from config
    bbox = (
        config['sar_data']['api_download']['target_glacier_bbox']['min_lon'],
        config['sar_data']['api_download']['target_glacier_bbox']['min_lat'],
        config['sar_data']['api_download']['target_glacier_bbox']['max_lon'],
        config['sar_data']['api_download']['target_glacier_bbox']['max_lat']
    )

    print(f"📍 Bounding box: {bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}")
    print()

    # Download parameters from config
    start_year = config['sar_data']['api_download']['start_year']
    end_year = config['sar_data']['api_download']['end_year']
    target_month = config['sar_data']['api_download']['target_month']
    polarization = config['sar_data']['api_download']['polarization']

    print(f"📅 Years: {start_year} - {end_year}")
    print(f"🗓️  Target month: {target_month} (summer melt season)")
    print(f"📡 Polarization: {polarization}")
    print()

    # Download the data
    downloaded_files = downloader.download_time_series(
        bbox=bbox,
        start_year=start_year,
        end_year=end_year,
        target_month=target_month,
        polarization=polarization,
        max_downloads=15  # Limit for this example
    )

    # Verify downloads
    verification = downloader.verify_downloads(downloaded_files)

    # Summary
    successful = sum(verification.values())
    total = len(verification)

    print("\n" + "=" * 80)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"📁 Files downloaded: {successful}/{total}")
    print(f"✅ Success rate: {successful/total*100:.1f}%" if total > 0 else "❌ No files processed")

    if successful > 0:
        print("
📋 Downloaded files:"        for filepath in downloaded_files:
            if verification[filepath]:
                print(f"  • {filepath}")

        print("
🚀 Ready for processing!"        print("💡 Next: Run 'python3 time_series_processor.py' to analyze the data"
    else:
        print("\n❌ No successful downloads")
        print("💡 Check your internet connection and ASF API availability")

    print("=" * 80)


def example_custom_download():
    """Example of custom API download with different parameters"""

    print("\n" + "=" * 80)
    print("🔧 CUSTOM DOWNLOAD EXAMPLE")
    print("=" * 80)
    print("Example of downloading data for a different glacier or time period")
    print("=" * 80)

    # Initialize downloader
    downloader = ASFAPIDownloader()

    # Custom bounding box for another glacier (example)
    custom_bbox = (74.45, 42.55, 74.55, 42.65)  # Example coordinates

    print(f"📍 Custom area: {custom_bbox}")
    print("📅 Custom period: 2020-2023")
    print("🗓️  Target month: 8 (August)")
    print()

    # Custom download
    custom_files = downloader.download_time_series(
        bbox=custom_bbox,
        start_year=2020,
        end_year=2023,
        target_month=8,
        polarization="VV+VH",
        max_downloads=5  # Just a few files for example
    )

    if custom_files:
        print(f"✅ Downloaded {len(custom_files)} files for custom area")
        for filepath in custom_files:
            print(f"  • {filepath}")
    else:
        print("❌ No files downloaded for custom area")

    print("=" * 80)


def example_small_test():
    """Example of small test download (quick verification)"""

    print("\n" + "=" * 80)
    print("🧪 SMALL TEST DOWNLOAD")
    print("=" * 80)
    print("Quick test with just 2 years of data")
    print("=" * 80)

    downloader = ASFAPIDownloader()

    # Small bounding box for testing
    test_bbox = (74.50, 42.56, 74.52, 42.58)  # Very small area

    print(f"📍 Test area: {test_bbox}")
    print("📅 Test period: 2022-2023 (2 years)")
    print()

    # Quick test download
    test_files = downloader.download_time_series(
        bbox=test_bbox,
        start_year=2022,
        end_year=2023,
        target_month=7,
        polarization="VV",
        max_downloads=3  # Just 3 files max
    )

    if test_files:
        print(f"✅ Test download successful: {len(test_files)} files")
        for filepath in test_files:
            print(f"  • {filepath}")
    else:
        print("❌ Test download failed - check connection")

    print("=" * 80)


if __name__ == "__main__":
    print("🚀 ASF API DOWNLOADER EXAMPLES")
    print("Testing different download scenarios for Sentinel-1 data")
    print()

    # Run examples
    example_api_download()
    example_custom_download()
    example_small_test()

    print("\n" + "=" * 80)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("📖 See asf_api_downloader.py for full implementation")
    print("📖 See time_series_processor.py for data analysis")
    print("📖 See run_full_pipeline.py for complete workflow")
    print("=" * 80)

