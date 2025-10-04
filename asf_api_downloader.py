#!/usr/bin/env python3
"""
ASF API Downloader for Sentinel-1 SAR Data
Automated download of time series data for glacier monitoring

This script downloads Sentinel-1 data for Golubina Glacier in Ala-Archa gorge
using the ASF (Alaska Satellite Facility) API for programmatic access.
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import logging
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASFAPIDownloader:
    """
    Downloads Sentinel-1 data from ASF using their REST API

    ASF API Documentation: https://docs.asf.alaska.edu/api/
    """

    def __init__(self, output_dir: str = "output/raw_data"):
        """
        Initialize the ASF API downloader

        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ASF API endpoint
        self.api_base = "https://api.daac.asf.alaska.edu"
        self.search_endpoint = f"{self.api_base}/services/search/param"

        # Request headers (no authentication required for search, but download may need credentials)
        self.headers = {
            'User-Agent': 'SAR-Glacier-Monitoring/1.0',
            'Content-Type': 'application/json'
        }

        logger.info(f"ASF API Downloader initialized. Output directory: {self.output_dir}")

    def search_granules(self, bbox: Tuple[float, float, float, float],
                       start_date: str, end_date: str,
                       polarization: str = "VV+VH",
                       platform: str = "Sentinel-1",
                       beam_mode: str = "IW",
                       processing_level: str = "GRD_HD") -> List[Dict]:
        """
        Search for Sentinel-1 granules using ASF API

        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            polarization: SAR polarization ("VV", "HH", "VV+VH", etc.)
            platform: Satellite platform ("Sentinel-1")
            beam_mode: Beam mode ("IW", "EW", etc.)
            processing_level: Processing level ("GRD_HD", "SLC", etc.)

        Returns:
            List of granule metadata dictionaries
        """
        logger.info(f"Searching granules for bbox {bbox}, dates {start_date} to {end_date}")

        # Build search parameters
        params = {
            'platform': platform,
            'processingLevel': processing_level,
            'beamMode': beam_mode,
            'polarization': polarization,
            'start': start_date,
            'end': end_date,
            'bbox': ','.join(map(str, bbox)),
            'output': 'json'
        }

        try:
            response = requests.get(self.search_endpoint, params=params, headers=self.headers)
            response.raise_for_status()

            results = response.json()
            granules = results.get('results', [])

            logger.info(f"Found {len(granules)} granules")
            return granules

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching granules: {e}")
            return []

    def filter_annual_summer_scenes(self, granules: List[Dict],
                                   target_month: int = 7) -> List[Dict]:
        """
        Filter granules to get one scene per year in the target month

        Args:
            granules: List of granule metadata
            target_month: Target month (1-12) for summer scenes

        Returns:
            Filtered list with one scene per year
        """
        logger.info(f"Filtering for annual scenes in month {target_month}")

        # Group by year
        scenes_by_year = {}
        for granule in granules:
            scene_date = granule.get('sceneDate', '')
            if scene_date:
                date_obj = datetime.strptime(scene_date, '%Y-%m-%d')
                year = date_obj.year
                month = date_obj.month

                # Only consider scenes from target month ±1 month
                if abs(month - target_month) <= 1:
                    if year not in scenes_by_year:
                        scenes_by_year[year] = []
                    scenes_by_year[year].append(granule)

        # For each year, select the scene closest to target month
        selected_scenes = []
        for year, year_scenes in scenes_by_year.items():
            if year_scenes:
                # Find scene closest to target month
                target_date = datetime(year, target_month, 15)  # Mid-month

                best_scene = min(year_scenes,
                               key=lambda x: abs(datetime.strptime(x['sceneDate'], '%Y-%m-%d') - target_date))

                selected_scenes.append(best_scene)
                logger.info(f"Selected {best_scene['sceneDate']} for year {year}")

        logger.info(f"Selected {len(selected_scenes)} annual scenes")
        return selected_scenes

    def download_granule(self, granule: Dict, download_dir: Optional[str] = None) -> bool:
        """
        Download a single granule

        Args:
            granule: Granule metadata dictionary
            download_dir: Custom download directory (optional)

        Returns:
            True if download successful, False otherwise
        """
        if download_dir:
            output_path = Path(download_dir)
        else:
            output_path = self.output_dir

        # Get download URL
        download_url = granule.get('downloadUrl', '')
        if not download_url:
            logger.error(f"No download URL for granule {granule.get('sceneDate', 'unknown')}")
            return False

        # Create filename
        scene_date = granule.get('sceneDate', 'unknown')
        filename = f"{granule.get('platform', 'S1')}_{granule.get('beamMode', 'IW')}_{scene_date}_{granule.get('polarization', 'VV')}.zip"
        filepath = output_path / filename

        # Check if file already exists
        if filepath.exists():
            logger.info(f"File already exists: {filepath}")
            return True

        logger.info(f"Downloading {filename}...")

        try:
            # Download file
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            # Write file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded: {filepath}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {filename}: {e}")
            return False

    def download_time_series(self, bbox: Tuple[float, float, float, float],
                           start_year: int, end_year: int,
                           target_month: int = 7,
                           polarization: str = "VV+VH",
                           max_downloads: int = 20) -> List[str]:
        """
        Download time series of Sentinel-1 data for multiple years

        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_year: Start year
            end_year: End year
            target_month: Target month for summer scenes (1-12)
            polarization: SAR polarization
            max_downloads: Maximum number of files to download

        Returns:
            List of downloaded file paths
        """
        logger.info(f"Starting time series download for {start_year}-{end_year}, month {target_month}")

        downloaded_files = []

        for year in range(start_year, end_year + 1):
            logger.info(f"Processing year {year}")

            # Define date range for this year
            start_date = f"{year}-{target_month-1:02d}-01" if target_month > 1 else f"{year}-01-01"
            end_date = f"{year}-{target_month+1:02d}-01" if target_month < 12 else f"{year}-12-31"

            # Search for granules
            granules = self.search_granules(bbox, start_date, end_date, polarization)

            if not granules:
                logger.warning(f"No granules found for year {year}")
                continue

            # Filter for annual scenes
            annual_scenes = self.filter_annual_summer_scenes(granules, target_month)

            if not annual_scenes:
                logger.warning(f"No suitable annual scenes found for year {year}")
                continue

            # Download the selected scene
            scene = annual_scenes[0]
            if self.download_granule(scene):
                scene_date = scene.get('sceneDate', 'unknown')
                filename = f"{scene.get('platform', 'S1')}_{scene.get('beamMode', 'IW')}_{scene_date}_{scene.get('polarization', 'VV')}.zip"
                downloaded_files.append(str(self.output_dir / filename))

                # Respect rate limits
                time.sleep(1)

            # Check download limit
            if len(downloaded_files) >= max_downloads:
                logger.info(f"Reached maximum download limit ({max_downloads})")
                break

        logger.info(f"Downloaded {len(downloaded_files)} files")
        return downloaded_files

    def verify_downloads(self, file_list: List[str]) -> Dict[str, bool]:
        """
        Verify that downloaded files exist and have reasonable size

        Args:
            file_list: List of file paths to verify

        Returns:
            Dictionary mapping file paths to verification status
        """
        logger.info("Verifying downloads...")

        verification = {}
        for filepath in file_list:
            path = Path(filepath)
            exists = path.exists()
            size_mb = path.stat().st_size / (1024 * 1024) if exists else 0

            verification[filepath] = exists and size_mb > 50  # Sentinel-1 files are typically >50MB

            status = "✅ OK" if verification[filepath] else "❌ FAILED"
            logger.info(f"{status}: {filepath} ({size_mb:.1f} MB)")

        return verification


def get_golubina_glacier_bbox() -> Tuple[float, float, float, float]:
    """
    Get bounding box for Golubina Glacier in Ala-Archa gorge

    Based on approximate location of Ala-Archa gorge and glacier positions.
    These coordinates may need refinement based on exact glacier location.

    Returns:
        Bounding box (min_lon, min_lat, max_lon, max_lat)
    """
    # Approximate coordinates for Ala-Archa gorge area
    # Golubina Glacier is located in the Ala-Archa gorge system
    # These coordinates cover the general area - may need adjustment

    min_lon = 74.45  # Western boundary
    min_lat = 42.50  # Southern boundary
    max_lon = 74.55  # Eastern boundary
    max_lat = 42.60  # Northern boundary

    logger.info(f"Golubina Glacier bounding box: {min_lon}, {min_lat}, {max_lon}, {max_lat}")

    return (min_lon, min_lat, max_lon, max_lat)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Download Sentinel-1 time series for glacier monitoring')
    parser.add_argument('--years', type=int, nargs=2, default=[2015, 2025],
                       help='Start and end years (default: 2015 2025)')
    parser.add_argument('--month', type=int, default=7,
                       help='Target month for summer scenes (1-12, default: 7)')
    parser.add_argument('--polarization', type=str, default='VV+VH',
                       help='SAR polarization (default: VV+VH)')
    parser.add_argument('--max-downloads', type=int, default=15,
                       help='Maximum number of files to download (default: 15)')
    parser.add_argument('--output-dir', type=str, default='output/raw_data',
                       help='Output directory (default: output/raw_data)')

    args = parser.parse_args()

    print("=" * 80)
    print("🔽 ASF API DOWNLOADER - Sentinel-1 Time Series")
    print("=" * 80)
    print(f"Target: Golubina Glacier, Ala-Archa Gorge")
    print(f"Years: {args.years[0]} - {args.years[1]}")
    print(f"Month: {args.month}")
    print(f"Polarization: {args.polarization}")
    print("=" * 80)

    # Initialize downloader
    downloader = ASFAPIDownloader(args.output_dir)

    # Get bounding box for Golubina Glacier
    bbox = get_golubina_glacier_bbox()

    # Download time series
    downloaded_files = downloader.download_time_series(
        bbox=bbox,
        start_year=args.years[0],
        end_year=args.years[1],
        target_month=args.month,
        polarization=args.polarization,
        max_downloads=args.max_downloads
    )

    # Verify downloads
    verification = downloader.verify_downloads(downloaded_files)

    # Summary
    successful = sum(verification.values())
    total = len(verification)

    print("\n" + "=" * 80)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {total}")
    print(f"Successful downloads: {successful}")
    print(f"Failed downloads: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%" if total > 0 else "No files processed")

    if successful > 0:
        print("\n✅ Downloaded files:")
        for filepath in downloaded_files:
            if verification[filepath]:
                print(f"  • {Path(filepath).name}")

        print(f"\n📁 Files saved to: {args.output_dir}")
        print("🚀 Ready for processing with sar_pipeline.py!"
    else:
        print("\n❌ No files were successfully downloaded.")
        print("💡 Check your internet connection and ASF API availability.")

    print("=" * 80)


if __name__ == "__main__":
    main()


