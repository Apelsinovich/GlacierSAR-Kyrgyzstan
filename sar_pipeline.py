#!/usr/bin/env python3
"""
SAR Processing Pipeline for Glacier Monitoring
Ala-Archa Gorge, Kyrgyzstan
NASA Space Apps Challenge 2025

This pipeline processes Sentinel-1 SAR data to monitor glacier melting
and changes over time using VV polarization.
"""

import os
import yaml
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import geopandas as gpd
from shapely.geometry import box
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SARGlacierPipeline:
    """
    Complete pipeline for SAR-based glacier monitoring
    
    Key Features:
    - Multi-temporal SAR image processing
    - Glacier boundary detection
    - Change detection and quantification
    - Melt rate estimation
    - Visualization and reporting
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize pipeline with configuration"""
        self.config = self._load_config(config_path)
        self.output_dir = Path(self.config['output']['base_directory'])
        self._create_directories()
        logger.info("SAR Glacier Pipeline initialized")
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _create_directories(self):
        """Create output directory structure"""
        for subdir in self.config['output']['subdirectories'].values():
            path = self.output_dir / subdir
            path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directories created at {self.output_dir}")
    
    def preprocess_sar_image(self, input_path: str, output_path: Optional[str] = None) -> np.ndarray:
        """
        Preprocess SAR image
        
        Steps:
        1. Read raw SAR data
        2. Radiometric calibration
        3. Speckle filtering
        4. Terrain correction (if DEM available)
        
        Args:
            input_path: Path to input SAR image
            output_path: Path to save preprocessed image
            
        Returns:
            Preprocessed SAR array
        """
        logger.info(f"Preprocessing SAR image: {input_path}")
        
        # Read SAR data
        with rasterio.open(input_path) as src:
            sar_data = src.read(1)  # Read first band
            profile = src.profile
            transform = src.transform
            crs = src.crs
        
        # Step 1: Radiometric calibration to Sigma0 (in dB)
        # Convert DN to backscatter coefficient
        sar_calibrated = self._calibrate_to_sigma0(sar_data)
        
        # Step 2: Speckle filtering
        filter_method = self.config['processing']['preprocessing']['speckle_filter']
        filter_size = self.config['processing']['preprocessing']['filter_size']
        
        if filter_method == "Lee":
            sar_filtered = self._lee_filter(sar_calibrated, filter_size)
        else:
            sar_filtered = sar_calibrated
        
        # Step 3: Convert to dB
        sar_db = 10 * np.log10(sar_filtered + 1e-10)
        
        # Save if output path provided
        if output_path:
            profile.update(dtype=rasterio.float32, count=1)
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(sar_db.astype(rasterio.float32), 1)
            logger.info(f"Preprocessed image saved to {output_path}")
        
        return sar_db
    
    def _calibrate_to_sigma0(self, sar_data: np.ndarray) -> np.ndarray:
        """
        Calibrate SAR data to Sigma0 backscatter coefficient
        
        Note: This is simplified. Real calibration requires
        calibration parameters from metadata.
        """
        # Simplified calibration (in practice, use proper calibration LUT)
        # For Sentinel-1 GRD: sigma0 = (DN^2) / calibration_constant
        sigma0 = np.square(sar_data.astype(float))
        return sigma0
    
    def _lee_filter(self, image: np.ndarray, window_size: int = 5) -> np.ndarray:
        """
        Apply Lee speckle filter
        
        The Lee filter reduces speckle while preserving edges
        """
        from scipy.ndimage import uniform_filter
        
        # Calculate local mean and variance
        mean = uniform_filter(image, window_size)
        sqr_mean = uniform_filter(image**2, window_size)
        variance = sqr_mean - mean**2
        
        # Overall variance
        overall_variance = np.var(image)
        
        # Lee filter weights
        weights = variance / (variance + overall_variance + 1e-10)
        filtered = mean + weights * (image - mean)
        
        return filtered
    
    def detect_glacier_boundaries(self, sar_image: np.ndarray, 
                                  threshold: Optional[float] = None) -> np.ndarray:
        """
        Detect glacier boundaries using thresholding
        
        Glaciers typically have higher backscatter (brighter in SAR)
        compared to surrounding terrain, especially in VV polarization.
        
        Args:
            sar_image: Preprocessed SAR image in dB
            threshold: Backscatter threshold in dB (auto if None)
            
        Returns:
            Binary mask of glacier areas
        """
        if threshold is None:
            threshold = self.config['processing']['detection']['threshold_value']
        
        logger.info(f"Detecting glaciers with threshold: {threshold} dB")
        
        # Simple thresholding (can be improved with ML)
        glacier_mask = sar_image > threshold
        
        # Morphological operations to clean up
        from scipy.ndimage import binary_opening, binary_closing
        glacier_mask = binary_opening(glacier_mask, structure=np.ones((3, 3)))
        glacier_mask = binary_closing(glacier_mask, structure=np.ones((3, 3)))
        
        return glacier_mask
    
    def compare_images(self, image1: np.ndarray, image2: np.ndarray, 
                      date1: str, date2: str) -> Dict:
        """
        Compare two SAR images to detect changes
        
        Methods:
        - Image differencing (dB difference)
        - Ratio method
        - Statistical analysis
        
        Args:
            image1: First SAR image (earlier date)
            image2: Second SAR image (later date)
            date1: Date of first image
            date2: Date of second image
            
        Returns:
            Dictionary with change metrics
        """
        logger.info(f"Comparing images: {date1} vs {date2}")
        
        # Image differencing
        difference = image2 - image1
        
        # Ratio method (in linear scale)
        image1_linear = 10 ** (image1 / 10)
        image2_linear = 10 ** (image2 / 10)
        ratio = image2_linear / (image1_linear + 1e-10)
        ratio_db = 10 * np.log10(ratio + 1e-10)
        
        # Statistical metrics
        mean_change = np.mean(difference)
        std_change = np.std(difference)
        max_decrease = np.min(difference)
        max_increase = np.max(difference)
        
        # Significant change areas
        threshold = self.config['processing']['change_detection']['significance_threshold']
        significant_decrease = difference < -threshold  # Potential melting
        significant_increase = difference > threshold
        
        results = {
            'date1': date1,
            'date2': date2,
            'difference_map': difference,
            'ratio_map': ratio_db,
            'statistics': {
                'mean_change_db': mean_change,
                'std_change_db': std_change,
                'max_decrease_db': max_decrease,
                'max_increase_db': max_increase,
                'percent_decreased': 100 * np.sum(significant_decrease) / difference.size,
                'percent_increased': 100 * np.sum(significant_increase) / difference.size
            },
            'change_masks': {
                'significant_decrease': significant_decrease,
                'significant_increase': significant_increase
            }
        }
        
        logger.info(f"Mean change: {mean_change:.2f} dB")
        logger.info(f"Areas with significant decrease: {results['statistics']['percent_decreased']:.2f}%")
        
        return results
    
    def calculate_glacier_area(self, glacier_mask: np.ndarray, 
                               pixel_size_m: float = 10.0) -> float:
        """
        Calculate glacier area from binary mask
        
        Args:
            glacier_mask: Binary mask of glacier
            pixel_size_m: Pixel size in meters (Sentinel-1 GRD: 10m)
            
        Returns:
            Area in km²
        """
        pixel_area_m2 = pixel_size_m ** 2
        total_area_m2 = np.sum(glacier_mask) * pixel_area_m2
        total_area_km2 = total_area_m2 / 1e6
        
        return total_area_km2
    
    def estimate_melt_rate(self, area_timeseries: List[Tuple[str, float]]) -> Dict:
        """
        Estimate glacier melt rate from time series
        
        Args:
            area_timeseries: List of (date, area_km2) tuples
            
        Returns:
            Melt rate statistics
        """
        if len(area_timeseries) < 2:
            return {'error': 'Need at least 2 measurements'}
        
        # Convert dates to datetime
        dates = [datetime.strptime(d, '%Y-%m-%d') for d, _ in area_timeseries]
        areas = [a for _, a in area_timeseries]
        
        # Linear regression
        from scipy.stats import linregress
        days = [(d - dates[0]).days for d in dates]
        slope, intercept, r_value, p_value, std_err = linregress(days, areas)
        
        # Convert to annual rate
        annual_rate_km2 = slope * 365.25
        percent_annual = (annual_rate_km2 / areas[0]) * 100 if areas[0] > 0 else 0
        
        results = {
            'annual_rate_km2': annual_rate_km2,
            'annual_rate_percent': percent_annual,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'total_change_km2': areas[-1] - areas[0],
            'total_change_percent': ((areas[-1] - areas[0]) / areas[0]) * 100 if areas[0] > 0 else 0
        }
        
        logger.info(f"Estimated melt rate: {annual_rate_km2:.3f} km²/year ({percent_annual:.2f}%/year)")
        
        return results
    
    def visualize_comparison(self, image1: np.ndarray, image2: np.ndarray,
                            change_results: Dict, output_path: str):
        """
        Create comprehensive visualization of image comparison
        
        Args:
            image1: First SAR image
            image2: Second SAR image
            change_results: Results from compare_images()
            output_path: Path to save figure
        """
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # Image 1
        im1 = axes[0, 0].imshow(image1, cmap='gray', vmin=-25, vmax=5)
        axes[0, 0].set_title(f"SAR Image 1\n{change_results['date1']}", fontsize=12, fontweight='bold')
        axes[0, 0].axis('off')
        plt.colorbar(im1, ax=axes[0, 0], label='Backscatter (dB)')
        
        # Image 2
        im2 = axes[0, 1].imshow(image2, cmap='gray', vmin=-25, vmax=5)
        axes[0, 1].set_title(f"SAR Image 2\n{change_results['date2']}", fontsize=12, fontweight='bold')
        axes[0, 1].axis('off')
        plt.colorbar(im2, ax=axes[0, 1], label='Backscatter (dB)')
        
        # Difference
        diff = change_results['difference_map']
        im3 = axes[0, 2].imshow(diff, cmap='RdYlBu_r', vmin=-5, vmax=5)
        axes[0, 2].set_title('Difference\n(Image2 - Image1)', fontsize=12, fontweight='bold')
        axes[0, 2].axis('off')
        plt.colorbar(im3, ax=axes[0, 2], label='Change (dB)')
        
        # Ratio
        ratio = change_results['ratio_map']
        im4 = axes[1, 0].imshow(ratio, cmap='RdYlBu_r', vmin=-3, vmax=3)
        axes[1, 0].set_title('Ratio (dB)', fontsize=12, fontweight='bold')
        axes[1, 0].axis('off')
        plt.colorbar(im4, ax=axes[1, 0], label='Ratio (dB)')
        
        # Significant changes
        change_map = np.zeros_like(diff)
        change_map[change_results['change_masks']['significant_decrease']] = -1
        change_map[change_results['change_masks']['significant_increase']] = 1
        
        im5 = axes[1, 1].imshow(change_map, cmap='RdBu_r', vmin=-1, vmax=1)
        axes[1, 1].set_title('Significant Changes\n(Blue: Decrease, Red: Increase)', 
                            fontsize=12, fontweight='bold')
        axes[1, 1].axis('off')
        cbar5 = plt.colorbar(im5, ax=axes[1, 1], ticks=[-1, 0, 1])
        cbar5.set_ticklabels(['Decrease', 'No Change', 'Increase'])
        
        # Statistics text
        stats = change_results['statistics']
        stats_text = f"""Change Statistics:
        
Mean Change: {stats['mean_change_db']:.2f} dB
Std Dev: {stats['std_change_db']:.2f} dB
Max Decrease: {stats['max_decrease_db']:.2f} dB
Max Increase: {stats['max_increase_db']:.2f} dB

Area Decreased: {stats['percent_decreased']:.2f}%
Area Increased: {stats['percent_increased']:.2f}%

Interpretation:
- Negative changes (blue) may indicate
  melting or moisture increase
- Positive changes (red) may indicate
  freezing or drying
"""
        
        axes[1, 2].text(0.05, 0.95, stats_text, transform=axes[1, 2].transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                       family='monospace')
        axes[1, 2].axis('off')
        
        plt.suptitle('SAR Image Comparison - Ala-Archa Glaciers\nNASA Space Apps Challenge 2025', 
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualization saved to {output_path}")
    
    def create_time_series_plot(self, area_timeseries: List[Tuple[str, float]], 
                               output_path: str):
        """
        Create time series plot of glacier area changes
        
        Args:
            area_timeseries: List of (date, area_km2) tuples
            output_path: Path to save figure
        """
        dates = [datetime.strptime(d, '%Y-%m-%d') for d, _ in area_timeseries]
        areas = [a for _, a in area_timeseries]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Absolute area
        ax1.plot(dates, areas, 'o-', linewidth=2, markersize=8, color='#2E86AB')
        ax1.set_ylabel('Glacier Area (km²)', fontsize=12, fontweight='bold')
        ax1.set_title('Glacier Area Time Series - Ala-Archa Glaciers', 
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Relative change
        if len(areas) > 0:
            baseline = areas[0]
            relative_change = [(a - baseline) / baseline * 100 for a in areas]
            
            ax2.plot(dates, relative_change, 'o-', linewidth=2, markersize=8, color='#A23B72')
            ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Relative Change (%)', fontsize=12, fontweight='bold')
            ax2.set_title('Relative Change from Baseline', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            
            # Color negative values red
            for i, (date, val) in enumerate(zip(dates, relative_change)):
                if val < 0:
                    ax2.plot(date, val, 'o', markersize=8, color='#F18F01')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Time series plot saved to {output_path}")
    
    def generate_report(self, results: Dict, output_path: str):
        """
        Generate comprehensive markdown report
        
        Args:
            results: Analysis results dictionary
            output_path: Path to save report
        """
        report = f"""# SAR Glacier Monitoring Report
## Ala-Archa Glaciers, Kyrgyzstan
### NASA Space Apps Challenge 2025

---

## 1. Study Area
- **Location**: {self.config['study_area']['name']}
- **Coordinates**: {self.config['study_area']['center_lat']}°N, {self.config['study_area']['center_lon']}°E
- **Glaciers Monitored**: {', '.join(self.config['study_area']['glaciers'])}

## 2. Data and Methodology

### SAR Data Specifications
- **Satellite**: {self.config['sar_data']['satellite']}
- **Polarization**: {self.config['sar_data']['polarization']} (recommended for glacier monitoring)
- **Product Type**: {self.config['sar_data']['product_type']}
- **Time Period**: {self.config['sar_data']['time_series']['start_date']} to {self.config['sar_data']['time_series']['end_date']}

### Why VV Polarization?
VV (Vertical transmit, Vertical receive) polarization is recommended for glacier monitoring because:
- **High sensitivity** to ice surface changes and roughness
- **Penetration depth** allows detection of sub-surface features
- **Snow water content** estimation capabilities
- **Melt detection** through backscatter changes
- **Consistent performance** across different glacier types

Alternative: HH polarization can be used for complementary information, and full polarimetric data (HH+HV+VH+VV) provides the most comprehensive analysis.

### Processing Pipeline
1. **Preprocessing**:
   - Radiometric calibration to Sigma0
   - {self.config['processing']['preprocessing']['speckle_filter']} filter for speckle reduction
   - Terrain correction using {self.config['processing']['preprocessing']['dem_source']}

2. **Glacier Detection**:
   - Thresholding method
   - Morphological operations for boundary refinement

3. **Change Detection**:
   - Image differencing
   - Ratio analysis
   - Statistical significance testing

4. **Time Series Analysis**:
   - Area quantification
   - Trend analysis
   - Melt rate estimation

## 3. Results

### Analysis Summary
"""
        
        if 'melt_rate' in results:
            mr = results['melt_rate']
            report += f"""
### Melt Rate Estimation
- **Annual melt rate**: {mr['annual_rate_km2']:.3f} km²/year ({mr['annual_rate_percent']:.2f}%/year)
- **Total change**: {mr['total_change_km2']:.3f} km² ({mr['total_change_percent']:.2f}%)
- **Statistical confidence**: R² = {mr['r_squared']:.3f}, p-value = {mr['p_value']:.4f}
"""
        
        if 'comparisons' in results:
            report += "\n### Multi-temporal Comparisons\n\n"
            for comp in results['comparisons']:
                stats = comp['statistics']
                report += f"""
#### {comp['date1']} vs {comp['date2']}
- Mean change: {stats['mean_change_db']:.2f} dB
- Areas with significant decrease: {stats['percent_decreased']:.2f}%
- Areas with significant increase: {stats['percent_increased']:.2f}%
"""
        
        report += """
## 4. Interpretation

### Backscatter Changes and Glacier Melting
- **Decrease in backscatter** (negative dB change): May indicate:
  - Surface melting and water accumulation
  - Increased moisture content
  - Change from dry to wet snow
  - Glacier surface smoothing

- **Increase in backscatter** (positive dB change): May indicate:
  - Freezing of melt water
  - Surface roughening
  - Snow accumulation
  - Exposed ice surfaces

### Seasonal Considerations
- **Spring/Summer**: Expect decreased backscatter due to melting
- **Fall/Winter**: Expect increased backscatter due to freezing

## 5. Impact Assessment

### Water Resources
- Glacier melt contributes to river flow in Ala-Archa gorge
- Changes affect water availability for Bishkek region
- Peak melt season impacts downstream communities

### Hazard Assessment
- Rapid melt can lead to glacial lake outburst floods (GLOFs)
- Changes in melt patterns affect river discharge variability
- Long-term glacier loss threatens sustainable water supply

## 6. Recommendations

1. **Continue Monitoring**: Regular SAR acquisitions for time series analysis
2. **Ground Validation**: Field measurements to validate SAR observations
3. **Multi-sensor Integration**: Combine with optical data and climate models
4. **Early Warning System**: Develop alerts for rapid change detection
5. **Community Engagement**: Share findings with local authorities and planners

## 7. References

- ESA Sentinel-1 Mission: https://sentinel.esa.int/web/sentinel/missions/sentinel-1
- Alaska Satellite Facility (ASF): https://search.asf.alaska.edu/
- NASA SAR Resources: https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Team**: TengriSpacers  
**Challenge**: Through the Radar Looking Glass - NASA Space Apps Challenge 2025
"""
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to {output_path}")


def main():
    """Main execution function"""
    print("=" * 80)
    print("SAR GLACIER MONITORING PIPELINE")
    print("Ala-Archa Glaciers, Kyrgyzstan")
    print("NASA Space Apps Challenge 2025")
    print("=" * 80)
    print()
    
    # Initialize pipeline
    pipeline = SARGlacierPipeline()
    
    print("Pipeline initialized successfully!")
    print(f"Output directory: {pipeline.output_dir}")
    print()
    print("POLARIZATION RECOMMENDATION: VV")
    print("VV polarization is optimal for glacier monitoring due to:")
    print("  - High sensitivity to ice/snow surface changes")
    print("  - Good penetration for sub-surface features")
    print("  - Excellent for detecting melt conditions")
    print()
    print("Next steps:")
    print("1. Download Sentinel-1 VV polarization data from ASF")
    print("2. Place data in ./output/raw_data/")
    print("3. Use pipeline methods for processing and analysis")
    print()
    print("Example usage:")
    print("  # Preprocess images")
    print("  img1 = pipeline.preprocess_sar_image('raw_data/image1.tif', 'preprocessed/image1_proc.tif')")
    print("  img2 = pipeline.preprocess_sar_image('raw_data/image2.tif', 'preprocessed/image2_proc.tif')")
    print()
    print("  # Compare images")
    print("  results = pipeline.compare_images(img1, img2, '2023-06-01', '2024-06-01')")
    print()
    print("  # Visualize")
    print("  pipeline.visualize_comparison(img1, img2, results, 'visualizations/comparison.png')")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()


