#!/usr/bin/env python3
"""
Example Workflow for SAR Glacier Analysis
Demonstrates complete pipeline from data to visualization

This script shows how to:
1. Load and preprocess multiple SAR images
2. Detect glacier boundaries
3. Compare images over time
4. Calculate melt rates
5. Generate visualizations and reports
"""

import numpy as np
from pathlib import Path
from sar_pipeline import SARGlacierPipeline


def example_workflow_simple():
    """
    Simple example: Compare two SAR images
    """
    print("=" * 80)
    print("EXAMPLE 1: Simple Two-Image Comparison")
    print("=" * 80)
    
    # Initialize pipeline
    pipeline = SARGlacierPipeline('config.yaml')
    
    # Example with synthetic data (replace with real data paths)
    print("\nStep 1: Preprocessing images...")
    
    # In real usage, replace these with actual file paths:
    # image1_path = 'raw_data/S1A_IW_GRDH_VV_20230601.tif'
    # image2_path = 'raw_data/S1A_IW_GRDH_VV_20240601.tif'
    
    # For demonstration, create synthetic SAR images
    image1 = create_synthetic_sar_image(size=(1000, 1000), glacier_position='center')
    image2 = create_synthetic_sar_image(size=(1000, 1000), glacier_position='center', 
                                       melt_factor=0.8)  # Simulated melting
    
    print("✓ Images loaded")
    
    # Step 2: Detect glaciers
    print("\nStep 2: Detecting glacier boundaries...")
    mask1 = pipeline.detect_glacier_boundaries(image1)
    mask2 = pipeline.detect_glacier_boundaries(image2)
    print(f"✓ Glacier detected in image 1: {np.sum(mask1)} pixels")
    print(f"✓ Glacier detected in image 2: {np.sum(mask2)} pixels")
    
    # Step 3: Calculate areas
    print("\nStep 3: Calculating glacier areas...")
    area1 = pipeline.calculate_glacier_area(mask1, pixel_size_m=10.0)
    area2 = pipeline.calculate_glacier_area(mask2, pixel_size_m=10.0)
    print(f"✓ Area in 2023: {area1:.2f} km²")
    print(f"✓ Area in 2024: {area2:.2f} km²")
    print(f"✓ Change: {area2 - area1:.2f} km² ({(area2-area1)/area1*100:.2f}%)")
    
    # Step 4: Compare images
    print("\nStep 4: Comparing images...")
    comparison = pipeline.compare_images(image1, image2, '2023-06-01', '2024-06-01')
    
    print(f"✓ Mean change: {comparison['statistics']['mean_change_db']:.2f} dB")
    print(f"✓ Areas with significant decrease: {comparison['statistics']['percent_decreased']:.2f}%")
    
    # Step 5: Visualize
    print("\nStep 5: Creating visualizations...")
    output_path = pipeline.output_dir / 'visualizations' / 'example_comparison.png'
    pipeline.visualize_comparison(image1, image2, comparison, str(output_path))
    print(f"✓ Visualization saved to {output_path}")
    
    print("\n" + "=" * 80)
    print("Example 1 completed successfully!")
    print("=" * 80)


def example_workflow_timeseries():
    """
    Advanced example: Time series analysis with multiple images
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Multi-temporal Time Series Analysis")
    print("=" * 80)
    
    # Initialize pipeline
    pipeline = SARGlacierPipeline('config.yaml')
    
    # Simulate multiple dates
    dates = [
        '2020-06-01', '2021-06-01', '2022-06-01', 
        '2023-06-01', '2024-06-01'
    ]
    
    print(f"\nAnalyzing {len(dates)} time points...")
    
    # Process each date
    areas = []
    for i, date in enumerate(dates):
        # Create synthetic data with progressive melting
        melt_factor = 1.0 - (i * 0.05)  # 5% reduction per year
        image = create_synthetic_sar_image(size=(1000, 1000), 
                                          glacier_position='center',
                                          melt_factor=melt_factor)
        
        mask = pipeline.detect_glacier_boundaries(image)
        area = pipeline.calculate_glacier_area(mask, pixel_size_m=10.0)
        areas.append(area)
        
        print(f"  {date}: {area:.2f} km²")
    
    # Create time series data
    area_timeseries = list(zip(dates, areas))
    
    # Estimate melt rate
    print("\nEstimating melt rate...")
    melt_stats = pipeline.estimate_melt_rate(area_timeseries)
    
    print(f"✓ Annual melt rate: {melt_stats['annual_rate_km2']:.3f} km²/year")
    print(f"✓ Annual percentage: {melt_stats['annual_rate_percent']:.2f}%/year")
    print(f"✓ Total change: {melt_stats['total_change_km2']:.3f} km² ({melt_stats['total_change_percent']:.2f}%)")
    print(f"✓ R²: {melt_stats['r_squared']:.3f}")
    
    # Create time series plot
    print("\nCreating time series visualization...")
    output_path = pipeline.output_dir / 'visualizations' / 'timeseries_example.png'
    pipeline.create_time_series_plot(area_timeseries, str(output_path))
    print(f"✓ Time series plot saved to {output_path}")
    
    # Generate report
    print("\nGenerating comprehensive report...")
    report_results = {
        'melt_rate': melt_stats,
        'comparisons': []
    }
    
    # Add pairwise comparisons
    for i in range(len(dates) - 1):
        melt_factor1 = 1.0 - (i * 0.05)
        melt_factor2 = 1.0 - ((i+1) * 0.05)
        img1 = create_synthetic_sar_image(size=(1000, 1000), melt_factor=melt_factor1)
        img2 = create_synthetic_sar_image(size=(1000, 1000), melt_factor=melt_factor2)
        
        comp = pipeline.compare_images(img1, img2, dates[i], dates[i+1])
        report_results['comparisons'].append(comp)
    
    report_path = pipeline.output_dir / 'reports' / 'glacier_analysis_report.md'
    pipeline.generate_report(report_results, str(report_path))
    print(f"✓ Report saved to {report_path}")
    
    print("\n" + "=" * 80)
    print("Example 2 completed successfully!")
    print("=" * 80)


def example_real_data_workflow():
    """
    Template for processing real Sentinel-1 data
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Real Data Processing Template")
    print("=" * 80)
    
    print("""
This is a template for processing real Sentinel-1 data.
Replace the file paths below with your actual data.

STEPS TO GET REAL DATA:

1. Go to Alaska Satellite Facility: https://search.asf.alaska.edu/
   
2. Search parameters:
   - Location: Ala-Archa, Kyrgyzstan (42.565°N, 74.5°E)
   - Dataset: Sentinel-1
   - Beam Mode: IW
   - Polarization: VV+VH (or just VV)
   - Product Type: GRD_HD
   - Date range: e.g., 2023-06-01 to 2024-06-30
   
3. Download 2-3 images from different dates
   
4. Place in ./output/raw_data/
   
5. Update the file paths below:
""")
    
    # Template code
    template = """
# Initialize pipeline
from sar_pipeline import SARGlacierPipeline
pipeline = SARGlacierPipeline('config.yaml')

# YOUR DATA PATHS (update these!)
image1_path = 'output/raw_data/S1A_IW_GRDH_1SDV_20230615_VV.tif'
image2_path = 'output/raw_data/S1A_IW_GRDH_1SDV_20240615_VV.tif'

# Preprocess
img1 = pipeline.preprocess_sar_image(
    image1_path, 
    'output/preprocessed/image_2023_processed.tif'
)

img2 = pipeline.preprocess_sar_image(
    image2_path,
    'output/preprocessed/image_2024_processed.tif'
)

# Detect glaciers
mask1 = pipeline.detect_glacier_boundaries(img1)
mask2 = pipeline.detect_glacier_boundaries(img2)

# Calculate areas
area1 = pipeline.calculate_glacier_area(mask1)
area2 = pipeline.calculate_glacier_area(mask2)

print(f"Glacier area 2023: {area1:.2f} km²")
print(f"Glacier area 2024: {area2:.2f} km²")
print(f"Change: {area2 - area1:.2f} km² ({(area2-area1)/area1*100:.2f}%)")

# Compare images
results = pipeline.compare_images(img1, img2, '2023-06-15', '2024-06-15')

# Visualize
pipeline.visualize_comparison(
    img1, img2, results,
    'output/visualizations/comparison_2023_2024.png'
)

# Generate report
pipeline.generate_report(
    {'comparisons': [results]},
    'output/reports/final_report.md'
)

print("Analysis complete! Check the output/ directory for results.")
"""
    
    print(template)
    
    print("\n" + "=" * 80)
    print("Save this template and adapt for your real data!")
    print("=" * 80)


def create_synthetic_sar_image(size=(1000, 1000), glacier_position='center', 
                               melt_factor=1.0):
    """
    Create synthetic SAR image for demonstration
    
    Args:
        size: Image dimensions (height, width)
        glacier_position: Position of glacier ('center', 'north', etc.)
        melt_factor: Factor to simulate melting (1.0 = no melt, 0.5 = 50% melt)
    
    Returns:
        Synthetic SAR image in dB
    """
    h, w = size
    image = np.random.randn(h, w) * 2 - 20  # Background noise
    
    # Create glacier region
    if glacier_position == 'center':
        y_center, x_center = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        
        # Elliptical glacier
        glacier_mask = ((x - x_center)**2 / (w/4)**2 + 
                       (y - y_center)**2 / (h/6)**2) < 1
        
        # Glacier backscatter (brighter)
        glacier_backscatter = -8 * melt_factor + np.random.randn(h, w) * 1.5
        
        # Apply glacier
        image[glacier_mask] = glacier_backscatter[glacier_mask]
    
    return image


def main():
    """Run all examples"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║           SAR GLACIER MONITORING - EXAMPLE WORKFLOWS                      ║")
    print("║           Ala-Archa Glaciers, Kyrgyzstan                                  ║")
    print("║           NASA Space Apps Challenge 2025                                  ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    
    try:
        # Run examples
        example_workflow_simple()
        example_workflow_timeseries()
        example_real_data_workflow()
        
        print("\n" + "=" * 80)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review the generated visualizations in output/visualizations/")
        print("2. Read the report in output/reports/")
        print("3. Download real Sentinel-1 data from ASF")
        print("4. Adapt Example 3 template for your real data")
        print("5. Create your presentation using the results!")
        print("\nGood luck with the NASA Space Apps Challenge! 🚀")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")


if __name__ == "__main__":
    main()


