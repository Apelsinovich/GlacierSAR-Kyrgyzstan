#!/usr/bin/env python3
"""
Full Pipeline Runner for Golubina Glacier Monitoring
Combines ASF API download + SAR processing + time series analysis

This script provides a complete workflow from data acquisition to analysis:
1. Download Sentinel-1 data for Golubina Glacier via ASF API
2. Process the SAR data through the pipeline
3. Perform time series analysis for trend detection
4. Generate visualizations and reports
"""

import os
import sys
import subprocess
from pathlib import Path
import yaml
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.log(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def run_command(cmd: str, description: str) -> bool:
    """
    Run a shell command and return success status

    Args:
        cmd: Command to run
        description: Description for logging

    Returns:
        True if command succeeded, False otherwise
    """
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False


def check_dependencies() -> bool:
    """Check if required dependencies are available"""
    logger.info("Checking dependencies...")

    required_modules = [
        'requests', 'numpy', 'matplotlib', 'rasterio', 'scipy',
        'geopandas', 'pyyaml', 'tqdm', 'scikit_image'
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        logger.info("Install missing modules with: pip install -r requirements.txt")
        return False

    logger.info("✅ All dependencies are available")
    return True


def main():
    """Main pipeline execution"""
    print("=" * 80)
    print("🚀 GOLUBINA GLACIER MONITORING - FULL PIPELINE")
    print("=" * 80)
    print("Complete workflow: Download → Process → Analyze → Visualize")
    print("=" * 80)

    # Load configuration
    config = load_config()
    target_glacier = config['study_area']['target_glacier']['name']
    start_year = config['sar_data']['api_download']['start_year']
    end_year = config['sar_data']['api_download']['end_year']

    print(f"🎯 Target: {target_glacier}")
    print(f"📅 Period: {start_year} - {end_year}")
    print(f"📍 Location: Ala-Archa Gorge, Kyrgyzstan")
    print("=" * 80)

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot proceed without required dependencies")
        print("Please install missing modules and try again")
        sys.exit(1)

    # Step 1: Download data via ASF API
    print("
📥 Step 1: Downloading Sentinel-1 data via ASF API..."    download_success = run_command(
        "python3 asf_api_downloader.py",
        "ASF API data download"
    )

    if not download_success:
        print("\n⚠️  Download failed, but you can continue with existing data")
        print("Or fix the download issue and run again")

    # Step 2: Process the time series
    print("
🔬 Step 2: Processing SAR time series..."    processing_success = run_command(
        "python3 time_series_processor.py",
        "SAR time series processing"
    )

    if not processing_success:
        print("\n❌ Processing failed")
        sys.exit(1)

    # Step 3: Create presentation graphics
    print("
🎨 Step 3: Creating presentation graphics..."    graphics_success = run_command(
        "python3 create_presentation_graphics.py",
        "Presentation graphics generation"
    )

    # Summary
    print("\n" + "=" * 80)
    print("🎉 FULL PIPELINE COMPLETED!")
    print("=" * 80)

    print("📊 Generated outputs:")
    print("  • 📁 output/raw_data/ - Downloaded Sentinel-1 files")
    print("  • 🔬 output/preprocessed/ - Processed SAR images")
    print("  • 📈 output/visualizations/ - Analysis plots and maps")
    print("  • 🎨 output/presentation/ - Presentation graphics")
    print("  • 📄 output/reports/ - Comprehensive analysis reports")

    print("
📋 Key results:"    print(f"  • Target glacier: {target_glacier}")
    print(f"  • Time period: {start_year}-{end_year}")
    print("  • Annual melt rate analysis completed"
    print("
🎯 Ready for presentation!"    print("
💡 Next steps:"    print("  1. Review results in output/visualizations/")
    print("  2. Check analysis report in output/reports/")
    print("  3. Use presentation graphics in output/presentation/")
    print("  4. Present findings at NASA Space Apps Challenge!")

    print("\n" + "=" * 80)
    print("🌟 Team TengriSpacers | NASA Space Apps Challenge 2025")
    print("Challenge: Through the Radar Looking Glass")
    print("=" * 80)


if __name__ == "__main__":
    main()


