#!/usr/bin/env python3
"""
Time Series Processor for Glacier Monitoring
Processes multiple SAR images over time for trend analysis

This script processes a time series of Sentinel-1 images for Golubina Glacier
to analyze melting patterns and trends over multiple years.
"""

import os
import yaml
import numpy as np
import rasterio
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Import our pipeline
from sar_pipeline import SARGlacierPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TimeSeriesProcessor:
    """
    Processes time series of SAR data for glacier monitoring

    Key features:
    - Batch processing of multiple SAR images
    - Temporal trend analysis
    - Melt rate calculation
    - Visualization of multi-year changes
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.pipeline = SARGlacierPipeline(config_path)
        self.output_dir = Path(self.config['output']['base_directory'])

        logger.info("Time Series Processor initialized")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def find_sar_files(self, data_dir: str = "output/raw_data") -> List[Path]:
        """
        Find all SAR files in the data directory

        Args:
            data_dir: Directory containing SAR data files

        Returns:
            List of file paths sorted by date
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            logger.warning(f"Data directory {data_path} does not exist")
            return []

        # Find all .zip files (Sentinel-1 downloads) and .tif files (processed)
        sar_files = []
        sar_files.extend(data_path.glob("*.zip"))
        sar_files.extend(data_path.glob("*.tif"))

        # Filter for Sentinel-1 files
        s1_files = []
        for file_path in sar_files:
            filename = file_path.name.upper()
            if 'S1' in filename and ('VV' in filename or 'VH' in filename):
                s1_files.append(file_path)

        # Sort by date (extract date from filename)
        def extract_date(filepath):
            filename = filepath.name
            # Try to extract date in format YYYYMMDD
            for part in filename.split('_'):
                if len(part) == 8 and part.isdigit():
                    try:
                        return datetime.strptime(part, '%Y%m%d')
                    except ValueError:
                        pass
            # Fallback: use file modification time
            return datetime.fromtimestamp(filepath.stat().st_mtime)

        s1_files.sort(key=extract_date)

        logger.info(f"Found {len(s1_files)} Sentinel-1 files")
        return s1_files

    def extract_sar_files(self, zip_files: List[Path], extract_dir: str = "output/raw_data") -> List[Path]:
        """
        Extract SAR data from zip files

        Args:
            zip_files: List of zip file paths
            extract_dir: Directory to extract files to

        Returns:
            List of extracted file paths
        """
        import zipfile

        extract_path = Path(extract_dir)
        extract_path.mkdir(parents=True, exist_ok=True)

        extracted_files = []

        for zip_path in zip_files:
            logger.info(f"Extracting {zip_path.name}")

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

                    # Find the extracted .tif files
                    for extracted_file in extract_path.glob("*.tif"):
                        if 'S1' in extracted_file.name.upper():
                            extracted_files.append(extracted_file)

            except zipfile.BadZipFile:
                logger.error(f"Failed to extract {zip_path}")
                continue

        logger.info(f"Extracted {len(extracted_files)} files")
        return extracted_files

    def process_time_series(self, file_list: List[Path],
                          target_glacier_bbox: Optional[Tuple[float, float, float, float]] = None) -> Dict:
        """
        Process time series of SAR images

        Args:
            file_list: List of SAR file paths
            target_glacier_bbox: Bounding box for target glacier (optional)

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing time series with {len(file_list)} files")

        if target_glacier_bbox is None:
            # Use target glacier bbox from config
            bbox = self.config['study_area']['target_glacier']['bounding_box']
            target_glacier_bbox = (bbox['min_lon'], bbox['min_lat'],
                                 bbox['max_lon'], bbox['max_lat'])

        results = {
            'dates': [],
            'areas': [],
            'mean_backscatter': [],
            'glacier_masks': [],
            'processing_dates': []
        }

        # Process each file
        for file_path in tqdm(file_list, desc="Processing time series"):
            try:
                # Extract date from filename
                filename = file_path.name
                date_str = None

                # Try different date formats in filename
                for part in filename.split('_'):
                    if len(part) == 8 and part.isdigit():
                        try:
                            date_obj = datetime.strptime(part, '%Y%m%d')
                            date_str = date_obj.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            pass

                if date_str is None:
                    logger.warning(f"Could not extract date from {filename}")
                    continue

                logger.info(f"Processing {filename} ({date_str})")

                # Preprocess image
                processed_path = self.output_dir / 'preprocessed' / f"{file_path.stem}_processed.tif"

                if not processed_path.exists():
                    # Preprocess the image
                    sar_image = self.pipeline.preprocess_sar_image(str(file_path), str(processed_path))
                else:
                    # Load preprocessed image
                    with rasterio.open(processed_path) as src:
                        sar_image = src.read(1)

                # Detect glacier boundaries
                glacier_mask = self.pipeline.detect_glacier_boundaries(sar_image)

                # Calculate area
                pixel_size = 10.0  # Sentinel-1 GRD pixel size in meters
                area_km2 = self.pipeline.calculate_glacier_area(glacier_mask, pixel_size)

                # Calculate mean backscatter for glacier area
                glacier_pixels = sar_image[glacier_mask]
                mean_backscatter = np.mean(glacier_pixels) if len(glacier_pixels) > 0 else np.nan

                # Store results
                results['dates'].append(date_str)
                results['areas'].append(area_km2)
                results['mean_backscatter'].append(mean_backscatter)
                results['glacier_masks'].append(glacier_mask)
                results['processing_dates'].append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                logger.info(f"  Area: {area_km2:.3f} km², Mean backscatter: {mean_backscatter:.2f} dB")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        logger.info(f"Successfully processed {len(results['dates'])} out of {len(file_list)} files")
        return results

    def analyze_trends(self, results: Dict) -> Dict:
        """
        Analyze trends in the time series data

        Args:
            results: Results dictionary from process_time_series

        Returns:
            Dictionary with trend analysis
        """
        logger.info("Analyzing trends in time series data")

        if len(results['dates']) < 2:
            logger.warning("Need at least 2 data points for trend analysis")
            return {}

        # Convert dates to datetime objects
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in results['dates']]
        areas = results['areas']
        backscatter = results['mean_backscatter']

        # Calculate area trends
        days = [(d - dates[0]).days for d in dates]

        # Linear regression for area
        from scipy.stats import linregress
        area_slope, area_intercept, area_r, area_p, area_std = linregress(days, areas)

        # Linear regression for backscatter
        valid_indices = [i for i, bs in enumerate(backscatter) if not np.isnan(bs)]
        if len(valid_indices) >= 2:
            bs_days = [days[i] for i in valid_indices]
            bs_values = [backscatter[i] for i in valid_indices]
            bs_slope, bs_intercept, bs_r, bs_p, bs_std = linregress(bs_days, bs_values)
        else:
            bs_slope = bs_intercept = bs_r = bs_p = bs_std = np.nan

        # Calculate annual rates
        days_per_year = 365.25
        area_annual_rate = area_slope * days_per_year
        bs_annual_rate = bs_slope * days_per_year

        trend_analysis = {
            'area_trend': {
                'slope_km2_per_day': area_slope,
                'annual_rate_km2_per_year': area_annual_rate,
                'r_squared': area_r ** 2,
                'p_value': area_p,
                'std_error': area_std,
                'total_change_km2': areas[-1] - areas[0] if len(areas) > 0 else 0,
                'relative_change_percent': ((areas[-1] - areas[0]) / areas[0] * 100) if areas[0] > 0 else 0
            },
            'backscatter_trend': {
                'slope_db_per_day': bs_slope,
                'annual_rate_db_per_year': bs_annual_rate,
                'r_squared': bs_r ** 2 if not np.isnan(bs_r) else np.nan,
                'p_value': bs_p if not np.isnan(bs_p) else np.nan,
                'std_error': bs_std if not np.isnan(bs_std) else np.nan,
                'mean_backscatter': np.nanmean(backscatter)
            },
            'summary': {
                'num_years': len(set([d.year for d in dates])),
                'date_range': f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}",
                'total_area_loss_km2': areas[0] - areas[-1] if len(areas) > 0 else 0,
                'average_annual_loss_km2': area_annual_rate
            }
        }

        logger.info(f"Area trend: {area_annual_rate:.4f} km²/year (R²={area_r**2:.3f})")
        logger.info(f"Backscatter trend: {bs_annual_rate:.4f} dB/year"        return trend_analysis

    def create_time_series_plots(self, results: Dict, trend_analysis: Dict,
                               output_dir: str = "output/visualizations") -> None:
        """
        Create comprehensive time series plots

        Args:
            results: Results dictionary
            trend_analysis: Trend analysis results
            output_dir: Output directory for plots
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # Plot 1: Glacier area over time
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in results['dates']]
        areas = results['areas']

        axes[0, 0].plot(dates, areas, 'o-', linewidth=2, markersize=8, color='#2E86AB')
        axes[0, 0].set_ylabel('Glacier Area (km²)', fontsize=12, fontweight='bold')
        axes[0, 0].set_title('Golubina Glacier Area Time Series', fontsize=14, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)

        # Add trend line
        if trend_analysis['area_trend']['r_squared'] > 0.1:
            days = [(d - dates[0]).days for d in dates]
            trend_line = [trend_analysis['area_trend']['slope_km2_per_day'] * day +
                         trend_analysis['area_trend']['intercept'] for day in days]
            axes[0, 0].plot(dates, trend_line, '--', color='red', alpha=0.7,
                           label=f'Trend: {trend_analysis["area_trend"]["annual_rate_km2_per_year"]:.3f} km²/year')
            axes[0, 0].legend()

        # Plot 2: Backscatter over time
        backscatter = results['mean_backscatter']
        valid_indices = [i for i, bs in enumerate(backscatter) if not np.isnan(bs)]

        if valid_indices:
            valid_dates = [dates[i] for i in valid_indices]
            valid_bs = [backscatter[i] for i in valid_indices]

            axes[0, 1].plot(valid_dates, valid_bs, 's-', linewidth=2, markersize=8, color='#A23B72')
            axes[0, 1].set_ylabel('Mean Backscatter (dB)', fontsize=12, fontweight='bold')
            axes[0, 1].set_title('Glacier Backscatter Time Series', fontsize=14, fontweight='bold')
            axes[0, 1].grid(True, alpha=0.3)

            # Add trend line for backscatter
            if trend_analysis['backscatter_trend']['r_squared'] > 0.1:
                bs_days = [(d - dates[0]).days for d in valid_dates]
                bs_trend = [trend_analysis['backscatter_trend']['slope_db_per_day'] * day +
                           trend_analysis['backscatter_trend']['intercept'] for day in bs_days]
                axes[0, 1].plot(valid_dates, bs_trend, '--', color='red', alpha=0.7,
                               label=f'Trend: {trend_analysis["backscatter_trend"]["annual_rate_db_per_year"]:.3f} dB/year')
                axes[0, 1].legend()

        # Plot 3: Area vs Backscatter correlation
        if valid_indices and len(areas) == len(backscatter):
            valid_areas = [areas[i] for i in valid_indices]

            axes[1, 0].scatter(valid_areas, valid_bs, alpha=0.7, s=100, color='#F18F01')
            axes[1, 0].set_xlabel('Glacier Area (km²)', fontsize=12, fontweight='bold')
            axes[1, 0].set_ylabel('Mean Backscatter (dB)', fontsize=12, fontweight='bold')
            axes[1, 0].set_title('Area vs Backscatter Correlation', fontsize=14, fontweight='bold')
            axes[1, 0].grid(True, alpha=0.3)

            # Add correlation coefficient
            if len(valid_areas) > 2:
                from scipy.stats import pearsonr
                corr, p_val = pearsonr(valid_areas, valid_bs)
                axes[1, 0].text(0.05, 0.95, f'r = {corr:.3f}\np = {p_val:.3f}',
                               transform=axes[1, 0].transAxes,
                               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                               verticalalignment='top', fontsize=10)

        # Plot 4: Summary statistics
        axes[1, 1].axis('off')

        summary_text = f"""
GOLUBINA GLACIER ANALYSIS SUMMARY

📊 Data Summary:
   • Time period: {trend_analysis['summary']['date_range']}
   • Number of observations: {len(results['dates'])}
   • Years covered: {trend_analysis['summary']['num_years']}

📉 Area Trends:
   • Total area loss: {trend_analysis['summary']['total_area_loss_km2']:.3f} km²
   • Average annual loss: {trend_analysis['summary']['average_annual_loss_km2']:.3f} km²/year
   • Trend significance: R² = {trend_analysis['area_trend']['r_squared']:.3f}
   • Statistical significance: p = {trend_analysis['area_trend']['p_value']:.4f}

📡 Backscatter Trends:
   • Mean backscatter: {trend_analysis['backscatter_trend']['mean_backscatter']:.2f} dB
   • Annual trend: {trend_analysis['backscatter_trend']['annual_rate_db_per_year']:.3f} dB/year
   • Trend significance: R² = {trend_analysis['backscatter_trend']['r_squared']:.3f}

🔬 Interpretation:
   • Negative area trend indicates glacier retreat
   • Backscatter trends may indicate surface changes
   • Strong correlation suggests coupled area/backscatter changes

📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        axes[1, 1].text(0.05, 0.95, summary_text, transform=axes[1, 1].transAxes,
                       fontsize=10, verticalalignment='top', family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        plt.suptitle('Golubina Glacier Long-term Monitoring - Ala-Archa Gorge\n' +
                    'NASA Space Apps Challenge 2025 | Time Series Analysis',
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()

        # Save plot
        plot_path = output_path / 'golubina_glacier_time_series.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Time series plot saved to {plot_path}")

        # Create simple trend plot for quick viewing
        plt.figure(figsize=(10, 6))

        # Area trend
        plt.subplot(1, 2, 1)
        plt.plot(dates, areas, 'o-', linewidth=2, markersize=8, color='#2E86AB')
        plt.ylabel('Area (km²)')
        plt.title('Glacier Area Trend')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

        # Backscatter trend (if available)
        if valid_indices:
            plt.subplot(1, 2, 2)
            plt.plot(valid_dates, valid_bs, 's-', linewidth=2, markersize=8, color='#A23B72')
            plt.ylabel('Backscatter (dB)')
            plt.title('Surface Backscatter Trend')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)

        plt.suptitle('Golubina Glacier Trends (2015-2025)', fontsize=14, fontweight='bold')
        plt.tight_layout()

        trend_plot_path = output_path / 'golubina_trends_simple.png'
        plt.savefig(trend_plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Simple trend plot saved to {trend_plot_path}")

        plt.close('all')

    def generate_report(self, results: Dict, trend_analysis: Dict,
                       output_dir: str = "output/reports") -> None:
        """
        Generate comprehensive analysis report

        Args:
            results: Results dictionary
            trend_analysis: Trend analysis results
            output_dir: Output directory for report
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_path = output_path / 'golubina_glacier_analysis.md'

        # Create report content
        report_content = f"""# Golubina Glacier Time Series Analysis Report
## Ala-Archa Gorge, Kyrgyzstan
### NASA Space Apps Challenge 2025

---

## 1. Study Overview

**Target Glacier**: Golubina Glacier
**Location**: Ala-Archa Gorge, Kyrgyzstan
**Coordinates**: 42.570°N, 74.510°E
**Analysis Period**: {trend_analysis['summary']['date_range']}
**Data Source**: Sentinel-1 SAR (VV+VH polarization)

---

## 2. Methodology

### Data Processing Pipeline:
1. **Download**: Automated ASF API download of Sentinel-1 data
2. **Preprocessing**: Radiometric calibration, speckle filtering, terrain correction
3. **Glacier Detection**: Threshold-based boundary detection
4. **Area Calculation**: Pixel-based area estimation (10m resolution)
5. **Trend Analysis**: Linear regression and statistical testing

### Technical Parameters:
- **Polarization**: VV+VH (dual polarization for enhanced classification)
- **Processing Level**: GRD_HD (Ground Range Detected, High Resolution)
- **Target Month**: July (peak summer melt season)
- **Temporal Coverage**: {trend_analysis['summary']['num_years']} years of observations

---

## 3. Results

### Glacier Area Analysis

| Metric | Value | Interpretation |
|--------|-------|---------------|
| **Initial Area** | {results['areas'][0]:.3f} km² | Baseline area at start of study period |
| **Final Area** | {results['areas'][-1]:.3f} km² | Current area at end of study period |
| **Total Loss** | {trend_analysis['summary']['total_area_loss_km2']:.3f} km² | Absolute area reduction |
| **Annual Rate** | {trend_analysis['summary']['average_annual_loss_km2']:.3f} km²/year | Average yearly loss rate |
| **Relative Loss** | {trend_analysis['area_trend']['relative_change_percent']:.1f}% | Percentage loss over study period |

### Statistical Analysis:
- **Trend Significance**: R² = {trend_analysis['area_trend']['r_squared']:.3f}
- **Statistical Test**: p-value = {trend_analysis['area_trend']['p_value']:.4f}
- **Standard Error**: ±{trend_analysis['area_trend']['std_error']:.4f} km²/year

### Backscatter Analysis:
- **Mean Backscatter**: {trend_analysis['backscatter_trend']['mean_backscatter']:.2f} dB
- **Annual Trend**: {trend_analysis['backscatter_trend']['annual_rate_db_per_year']:.3f} dB/year
- **Trend Significance**: R² = {trend_analysis['backscatter_trend']['r_squared']:.3f}

---

## 4. Interpretation

### Glacier Dynamics:
- **Area Reduction**: {trend_analysis['summary']['total_area_loss_km2']:.3f} km² loss over {trend_analysis['summary']['num_years']} years
- **Melt Rate**: {abs(trend_analysis['summary']['average_annual_loss_km2']):.3f} km²/year average loss
- **Relative Rate**: {abs(trend_analysis['area_trend']['relative_change_percent']):.1f}% annual reduction

### Surface Changes:
- **Backscatter Trend**: {trend_analysis['backscatter_trend']['annual_rate_db_per_year']:+.3f} dB/year change
- **Surface Roughness**: {'Increasing' if trend_analysis['backscatter_trend']['annual_rate_db_per_year'] > 0 else 'Decreasing'} surface roughness
- **Moisture Content**: {'Increasing' if trend_analysis['backscatter_trend']['annual_rate_db_per_year'] < 0 else 'Decreasing'} surface moisture

### Climate Implications:
- **Water Resources**: Reduced glacier area affects downstream water availability
- **Flood Risk**: Glacier retreat may increase flood vulnerability
- **Ecosystem Impact**: Changes affect local flora and fauna

---

## 5. Technical Validation

### Data Quality:
- **Number of Observations**: {len(results['dates'])} valid measurements
- **Temporal Coverage**: {len(set([datetime.strptime(d, '%Y-%m-%d').year for d in results['dates']]))} unique years
- **Processing Success Rate**: {len(results['dates'])/len(results['processing_dates'])*100:.1f}% of files processed successfully

### Methodology Validation:
- **Area Calculation**: Based on pixel counting with 10m Sentinel-1 resolution
- **Trend Analysis**: Linear regression with statistical significance testing
- **Backscatter Analysis**: Mean values for glacier pixels only

---

## 6. Recommendations

### For Local Authorities:
1. **Monitor Annually**: Continue annual monitoring during July-August
2. **Field Validation**: Ground measurements to validate SAR estimates
3. **Water Management**: Plan for reduced summer water availability
4. **Hazard Assessment**: Evaluate flood risks from glacier changes

### For Researchers:
1. **Extended Time Series**: Continue monitoring for long-term trends
2. **Multi-Sensor Integration**: Combine SAR with optical data
3. **Climate Modeling**: Correlate with temperature and precipitation data
4. **Process Studies**: Investigate physical processes driving changes

---

## 7. Data Availability

### Processed Data:
- **Raw Files**: Located in `output/raw_data/`
- **Processed Images**: Located in `output/preprocessed/`
- **Analysis Results**: Available in `output/visualizations/`

### Visualization Files:
- `golubina_glacier_time_series.png` - Comprehensive time series plots
- `golubina_trends_simple.png` - Simplified trend visualization

---

## 8. References

- ASF API Documentation: https://docs.asf.alaska.edu/api/
- Sentinel-1 Mission: https://sentinel.esa.int/web/sentinel/missions/sentinel-1
- Glacier Monitoring Literature: Nagler et al. (2015), Winsvold et al. (2018)

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Processing Pipeline**: SAR Glacier Monitoring System v1.0

**Team**: TengriSpacers
**Challenge**: Through the Radar Looking Glass - NASA Space Apps Challenge 2025
"""

        # Write report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Analysis report saved to {report_path}")


def main():
    """Main execution function"""
    print("=" * 80)
    print("🕐 GOLUBINA GLACIER TIME SERIES PROCESSOR")
    print("=" * 80)
    print("Processing Sentinel-1 data for long-term glacier monitoring")
    print("Target: Golubina Glacier, Ala-Archa Gorge (2015-2025)")
    print("=" * 80)

    # Initialize processor
    processor = TimeSeriesProcessor()

    # Find SAR files
    print("\n📁 Step 1: Finding SAR data files...")
    sar_files = processor.find_sar_files()

    if not sar_files:
        print("❌ No SAR files found. Please run asf_api_downloader.py first.")
        return

    print(f"✅ Found {len(sar_files)} SAR files")

    # Extract zip files if needed
    zip_files = [f for f in sar_files if f.suffix == '.zip']
    if zip_files:
        print(f"\n📦 Step 2: Extracting {len(zip_files)} zip files...")
        extracted_files = processor.extract_sar_files(zip_files)
        tif_files = [f for f in sar_files if f.suffix == '.tif'] + extracted_files
    else:
        tif_files = sar_files

    print(f"✅ Ready to process {len(tif_files)} image files")

    # Process time series
    print("
🔬 Step 3: Processing time series..."    results = processor.process_time_series(tif_files)

    if not results['dates']:
        print("❌ No valid data processed. Check file formats and paths.")
        return

    # Analyze trends
    print("
📊 Step 4: Analyzing trends..."    trend_analysis = processor.analyze_trends(results)

    # Create visualizations
    print("
📈 Step 5: Creating visualizations..."    processor.create_time_series_plots(results, trend_analysis)

    # Generate report
    print("
📄 Step 6: Generating analysis report..."    processor.generate_report(results, trend_analysis)

    # Summary
    print("\n" + "=" * 80)
    print("✅ TIME SERIES ANALYSIS COMPLETED!")
    print("=" * 80)
    print(f"📊 Processed {len(results['dates'])} observations")
    print(f"📅 Time period: {trend_analysis['summary']['date_range']}")
    print(f"📉 Annual area loss: {trend_analysis['summary']['average_annual_loss_km2']:.3f} km²/year")
    print(f"📁 Results saved to: output/visualizations/ and output/reports/")
    print("=" * 80)


if __name__ == "__main__":
    main()


