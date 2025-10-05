# 🚀 Quick Start: Checklist (10 minutes)

## ✅ STEP 1: Installation (2 minutes)
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Install main libraries
pip3 install numpy matplotlib scipy rasterio geopandas pyyaml

# Check functionality
python3 sar_pipeline.py  # Should output welcome message
```

## ✅ STEP 2: Data (3 minutes)
```bash
# 1. Go to https://search.asf.alaska.edu/
# 2. Enter coordinates: 42.565, 74.5 (Ala-Archa)
# 3. Filters:
#    - Dataset: Sentinel-1
#    - Polarization: VV+VH (or VV)
#    - Product: GRD_HD
#    - Dates: June 2023 + June 2024
# 4. Download 2 files
# 5. Place in output/raw_data/
```

## ✅ STEP 3: Test run (2 minutes)
```bash
# Run examples with synthetic data
python3 example_workflow.py

# Results will appear in output/visualizations/
```

## ✅ STEP 3.1: Automated download (5 minutes)
```bash
# Download 10 years of data for Golubina Glacier
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Or run the full pipeline automatically
python3 run_full_pipeline.py
```

## ✅ STEP 5: Real analysis (3 minutes)
```python
from sar_pipeline import SARGlacierPipeline

# Initialize
pipeline = SARGlacierPipeline('config.yaml')

# Load your data
img1 = pipeline.preprocess_sar_image('output/raw_data/your_file_2023.tif')
img2 = pipeline.preprocess_sar_image('output/raw_data/your_file_2024.tif')

# Analyze changes
results = pipeline.compare_images(img1, img2, '2023-06-01', '2024-06-01')

# Visualize
pipeline.visualize_comparison(img1, img2, results, 'output/comparison.png')

print("Done! Check output/visualizations/")
```

---

## 🎯 MAIN: VV POLARIZATION
**Use VV (Vertical-Vertical)** Sentinel-1 polarization for optimal glacier melting detection!

**Why VV?**
- ✅ Maximum sensitivity to melt water
- ✅ High contrast between dry and wet ice
- ✅ Available in 100% of Sentinel-1 images

---

## 📁 Project structure
```
GlacierSAR-Kyrgyzstan/
├── sar_pipeline.py          # Main code
├── config.yaml             # Configuration
├── example_workflow.py     # Examples
├── requirements.txt        # Dependencies
├── QUICK_START.md          # Detailed guide
└── output/                 # Results
```

---

## 🔧 If problems

### Import error:
```bash
pip3 install rasterio geopandas scikit-image
```

### No data:
```bash
# Automatically download 10 years of data:
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Or download manually from ASF (see QUICK_START.md)
# Or use synthetic data from example_workflow.py
```

### Questions:
- See `QUICK_START.md` for details
- See `DEBRIS_CLASSIFICATION.md` for improved classification

---

## 🎉 DONE!
Now you have a working pipeline for monitoring Ala-Archa glaciers using SAR data!

**Next steps:**
1. Automatically download 10 years of data: `python3 asf_api_downloader.py --years 2015 2025 --month 7`
2. Process time series: `python3 time_series_processor.py`
3. Or run the full pipeline: `python3 run_full_pipeline.py`
4. Create presentation with results
5. Profit! 🚀

---

**Команда TengriSpacers** | **NASA Space Apps Challenge 2025**


