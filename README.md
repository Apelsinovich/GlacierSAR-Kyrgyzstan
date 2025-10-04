# GlacierSAR-Kyrgyzstan 🏔️❄️

Glacier monitoring and analysis system for Kyrgyzstan using Sentinel-1 SAR data and AI/ML techniques.

**Mission**: Monitor glacier changes in the Ala-Archa Gorge and Tien Shan region to:
- Track glacier melt rates and boundary changes over time
- Predict future trends and assess climate impacts
- Support disaster mitigation and water resource management
- Provide actionable insights for authorities, planners, and communities

---

## 📁 Project Structure

```
GlacierSAR-Kyrgyzstan/
├── data_processing/          # Scripts for downloading and processing SAR data
│   ├── download_sentinel1_data.py      # Download Sentinel-1 from ASF
│   ├── sentinel1_to_png.py             # Convert SAR data to PNG images
│   ├── extract_polygon_region.py       # Extract specific regions
│   └── sentinel1_analyzer.py           # Analyze glacier characteristics
├── glacier_detection/        # Glacier detection and segmentation algorithms
│   ├── dinov3_glacier_segmentation.py  # Main DINOv3-based detection
│   ├── dinov3_border_detection.py      # Border detection with DINOv3
│   └── traditional_cv_detection.py     # Traditional CV approach
├── prediction/              # Time-series prediction and trend analysis
│   ├── glacier_trend_predictor.py      # Trend analysis and forecasting
│   └── pixel_based_predictor.py        # Pixel-level predictions
├── examples/                # Example scripts and tutorials
│   ├── dinov3_basic_example.py         # Basic DINOv3 usage
│   └── dinov3_quantized_example.py     # Quantized model example
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd GlacierSAR-Kyrgyzstan

# Install dependencies
pip install -r requirements.txt
```

### Basic Workflow

1. **Download Sentinel-1 data** → `data_processing/download_sentinel1_data.py`
2. **Convert to PNG images** → `data_processing/sentinel1_to_png.py`
3. **Detect glaciers** → `glacier_detection/dinov3_glacier_segmentation.py`
4. **Predict trends** → `prediction/glacier_trend_predictor.py`

---

## 📚 Module Documentation

### 1. Data Processing (`data_processing/`)

#### `download_sentinel1_data.py`
Downloads Sentinel-1 SAR data from Alaska Satellite Facility (ASF) for your area of interest.

**Features:**
- Filters data by month (e.g., August for end-of-melt season)
- Selects one image per year automatically
- Configurable polygon region (WKT format)
- Uses ASF Search API

**Configuration:**
```python
wkt_aoi = 'POLYGON ((...))'  # Your area of interest
target_month = 8              # August
start_date = '2014-01-01'
end_date = '2025-12-31'
pass_direction = asf.FLIGHT_DIRECTION.ASCENDING
download_folder = 'kyrgyzstan_glacier_data'
```

**Usage:**
```bash
python data_processing/download_sentinel1_data.py
```

---

#### `sentinel1_to_png.py`
Converts Sentinel-1 ZIP files to high-resolution PNG images with two modes.

**Features:**
- **QUICKLOOK mode**: Extracts built-in preview images (fastest, low-res)
- **RAW DATA mode**: Processes measurement data with custom settings (HIGH-RES)
- VV or VH polarization support (VV recommended for glaciers)
- Automatic contrast enhancement using percentile stretching
- dB scale conversion for better visualization
- Automatic downsampling if file size exceeds 30 MB threshold
- 8-bit compression for smaller files

**Configuration:**
```python
input_folder = '../kyrgyzstan_glacier_data'
output_folder = '../sentinel_pngs_highres'
polarization = 'vv'                    # VV is best for glacier/ice
contrast_percentile = (2, 98)          # Contrast stretching
output_dpi = 300                       # High resolution
max_size_mb = 30                       # Auto-downsample threshold
use_quicklook = False                  # False for high-res raw data
```

**Usage:**
```bash
python data_processing/sentinel1_to_png.py
```

---

#### `extract_polygon_region.py`
Extracts a specific polygon region from Sentinel-1 data and creates separate outputs for multiple polarizations.

**Features:**
- Polygon-based spatial extraction
- Multi-polarization support (VV, VH, HH)
- Geo-referencing preserved
- Contrast enhancement per polarization

**Usage:**
```bash
python data_processing/extract_polygon_region.py
```

---

#### `sentinel1_analyzer.py`
Analyzes processed Sentinel-1 data for glacier characteristics and temporal changes.

**Features:**
- Glacier threshold detection using backscatter values
- Area calculations and statistics
- Time-series analysis
- Works with SNAP-processed data or GeoTIFFs

**Usage:**
```bash
python data_processing/sentinel1_analyzer.py
```

---

### 2. Glacier Detection (`glacier_detection/`)

#### `dinov3_glacier_segmentation.py` ⭐ (Main Detection Script)
Advanced glacier segmentation using Meta's DINOv3 vision transformer model.

**Features:**
- Self-supervised learning approach (no labeled data needed)
- Uses DINOv3-ViT-L/16 pre-trained on satellite imagery
- Patch-based dense feature extraction (16x16 patches)
- CLS-patch similarity mapping for glacier identification
- Multi-cue fusion (CLS similarity + HSV color + edge detection)
- GMM clustering for probabilistic segmentation
- Random Walker algorithm for boundary refinement
- Morphological operations for noise removal

**How it works:**
1. Loads image and processes with DINOv3
2. Extracts CLS token and patch features
3. Computes similarity between CLS and all patches
4. Combines with HSV color space and Sobel edges
5. Applies 2-component GMM clustering
6. Performs morphological refinement (opening/closing)
7. Uses Random Walker for precise boundaries
8. Saves multiple output visualizations

**Usage:**
```bash
python glacier_detection/dinov3_glacier_segmentation.py
```

**Output files:**
- `glacier_mask.png` - Binary segmentation mask
- `glacier_probability.png` - Probability heatmap
- `glacier_edges.png` - Edge detection result
- `dinov3_glacier_segment.png` - Final visualization
- `saliency_map.png` - CLS-patch similarity map

---

#### `dinov3_border_detection.py`
Specialized script for detecting glacier boundaries using DINOv3 features and K-means clustering.

**Features:**
- Dense feature extraction with multiple DINOv3 variants
- K-means clustering for glacier/non-glacier separation
- Border detection with morphological operations
- Coordinate extraction for glacier boundaries

**Usage:**
```bash
python glacier_detection/dinov3_border_detection.py
```

---

#### `traditional_cv_detection.py`
Traditional computer vision approach for glacier detection without deep learning.

**Features:**
- Color and brightness thresholding
- HSV and LAB color space analysis
- Edge detection using Sobel filters
- Morphological operations
- Fast and interpretable results

**Best for:**
- Quick prototyping and testing
- High-contrast glacier images
- Limited computational resources

**Usage:**
```bash
python glacier_detection/traditional_cv_detection.py --image glacier.png
```

---

### 3. Prediction (`prediction/`)

#### `glacier_trend_predictor.py`
Analyzes glacier time-series data and predicts future trends using regression models.

**Features:**
- Loads multi-year glacier images from directory
- Extracts multiple metrics (area, brightness, edge length, etc.)
- Polynomial regression for trend forecasting
- CSV data integration for ground truth
- Visualization of historical trends and predictions

**Usage:**
```bash
python prediction/glacier_trend_predictor.py
```

---

#### `pixel_based_predictor.py`
Advanced pixel-by-pixel prediction for high-resolution glacier forecasting.

**Features:**
- Individual time-series model per pixel location
- Multiple model types: Linear, Polynomial (default), Random Forest
- Preserves spatial patterns and details
- Full resolution output predictions

**Usage:**
```python
from prediction.pixel_based_predictor import PixelBasedGlacierPredictor

predictor = PixelBasedGlacierPredictor(pngs_dir='./pngs')
predictor.load_images()
predictions = predictor.predict_pixel_by_pixel(
    target_years=[2026, 2027, 2028],
    model_type='polynomial',
    degree=2
)
```

---

### 4. Examples (`examples/`)

#### `dinov3_basic_example.py`
Minimal example demonstrating DINOv3 feature extraction.

**Usage:**
```bash
python examples/dinov3_basic_example.py
```

---

#### `dinov3_quantized_example.py`
Example using Int4 quantized DINOv3 model for efficient inference.

**Features:**
- Int4 weight quantization with TorchAO
- Reduced memory footprint (~4x smaller)
- Faster inference on CPU

**Usage:**
```bash
pip install torchao
python examples/dinov3_quantized_example.py
```

---

## 🛠️ Technical Details

### SAR Polarizations

**VV (Vertical-Vertical)**: Best for glacier and ice detection - recommended for this project

**VH (Vertical-Horizontal)**: Good for texture and roughness analysis

**HH (Horizontal-Horizontal)**: Additional information for multi-polarization analysis

### Data Sources

**Sentinel-1 SAR**
- C-band synthetic aperture radar (5.405 GHz)
- Resolution: 10m ground range detected
- Repeat cycle: 6-12 days
- Free and open data via Copernicus

**Alaska Satellite Facility (ASF)**
- NASA's DAAC for SAR data
- Complete Sentinel-1 archive since 2014
- API for automated downloads

---

## 📊 Typical Workflow

```bash
# Step 1: Download Sentinel-1 data
cd data_processing
python download_sentinel1_data.py

# Step 2: Convert to PNG images
python sentinel1_to_png.py

# Step 3: Detect glaciers using DINOv3
cd ../glacier_detection
python dinov3_glacier_segmentation.py

# Step 4: Analyze trends and predict
cd ../prediction
python glacier_trend_predictor.py
```

---

## 🎯 Use Cases

1. **Glacier Monitoring**: Track glacier extent changes over years
2. **Climate Impact Assessment**: Quantify melt rates and trends
3. **Water Resource Management**: Predict future water availability
4. **Disaster Risk Assessment**: Identify potential glacial lake outburst floods (GLOFs)
5. **Scientific Research**: Analyze glacier dynamics in the Tien Shan region

---

## 🔬 Methodology

### Why DINOv3?

- Self-supervised learning (no labeled data needed)
- Pre-trained on 493M satellite images
- Dense feature extraction captures fine details
- Transfer learning generalizes to unseen glaciers

### Why SAR over Optical?

- All-weather capability (works through clouds)
- Day/night operation (independent of sunlight)
- Ice sensitivity (C-band radar detects ice well)
- Temporal consistency (regular revisits)
- Free and open data

---

## 🤝 Team

**TengriSpacers** - NASA Space Apps Challenge 2025

- **Dmitrii Pecherkin** — Team Lead & Infrastructure Engineer
- **Mikhail Vasilyev** — Developer (SAR data extraction & analysis)
- **Farit Gatiatullin** — Developer (SAR implementation & research)
- **Kenenbek Arzymatov** — Data Scientist (ML/AI & predictions)
- **Juozas Bechelis** — Contributor (ideas & infrastructure)

**Team page:** [TengriSpacers on NASA Space Apps Challenge](https://www.spaceappschallenge.org/2025/find-a-team/tengrispacers/)

---

## 🔗 Links & Resources

### NASA Resources
- [Intro to Synthetic Aperture Radar (SAR)](https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar)
- [Alaska Satellite Facility (ASF) Data Search Vertex](https://search.asf.alaska.edu/)
- [SAR StoryMaps](https://nisar.jpl.nasa.gov/applications/arcgis-storymaps/)

### Tools & Software
- [QGIS](https://qgis.org) - GIS visualization
- [nakarte.me](https://nakarte.me/) - Topographic maps
- [Google Maps](https://www.google.com/maps) - Reference imagery

### AI/ML Resources
- [DINOv3](https://ai.meta.com/dinov3/) - Vision transformer model
- [GitHub Copilot](https://copilot.microsoft.com/) - Development assistance
- [ChatGPT](https://chat.openai.com/) - Research support
- [Grok](https://grok.com/) - Research and problem-solving

---

## 📝 Citation

```bibtex
@misc{glaciersar-kyrgyzstan2025,
  title={GlacierSAR-Kyrgyzstan: Glacier Monitoring Using Sentinel-1 SAR and DINOv3},
  author={TengriSpacers Team},
  year={2025},
  howpublished={NASA Space Apps Challenge 2025},
  url={https://www.spaceappschallenge.org/2025/find-a-team/tengrispacers/}
}
```

---

## 🆘 Support & Troubleshooting

### Common Issues

**Issue: "No module named 'transformers'"**
```bash
pip install transformers torch pillow
```

**Issue: "CUDA out of memory"**
- Use smaller DINOv3 model (ViT-S instead of ViT-L)
- Reduce image resolution before processing
- Use quantized models (see examples)

**Issue: "Download requires Earthdata credentials"**
- Create account at https://urs.earthdata.nasa.gov/
- Add credentials to `~/.netrc` file

**Issue: PNG files too large**
- Adjust `max_size_mb` parameter in scripts
- Use QUICKLOOK mode for lower resolution
- Enable automatic downsampling

---

## 🌍 Impact

This project aims to:
- Support authorities and planners in disaster mitigation
- Raise awareness of glacier melt and climate impacts
- Provide actionable insights for scientists and communities
- Enable monitoring of critical water resources

The techniques developed here can be adapted for glacier monitoring in other mountain regions worldwide, contributing to global climate change research and adaptation efforts.

---

**Note**: This project demonstrates how freely available satellite data (Sentinel-1) combined with state-of-the-art AI models (DINOv3) can address critical climate challenges in Central Asia and beyond. 🌏🛰️

