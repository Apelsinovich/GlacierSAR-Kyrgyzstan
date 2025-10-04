# Through the Radar Looking Glass: Revealing Earth Processes with SAR  
## NASA Hackathon 2025 — Ala-Archa Glaciers Melting & Impact on Bishkek, Kyrgyzstan

---

## 1. Project Overview

We use SAR data to monitor and forecast glacier melt in the Ala-Archa gorge, which is fed by multiple glaciers including Adigine, Ak-Sai, Golubina, Toktogul, Big Ala-Archa, Small Ala-Archa, and others.  

**Approach:**  
- Analyze historical melt patterns and predict future changes  
- Generate time-series visualizations and graphs showing melt rates  
- Model impacts on the gorge’s river, water resources, floods, and nearby communities  
- Explore how this methodology could be adapted to other glacial systems  

**Impact:**  
- Demonstrates HOW glaciers in the Ala-Archa region are melting and the resulting effects on water supply and local hazards  
- Supports authorities and planners in disaster mitigation and strategic decision-making  
- Raises awareness of glacier melt and climate impacts in the region, providing actionable insights for scientists and communities
---

## 2. Demo

- 🎯 **SAR Processing Pipeline**: Complete Python pipeline for glacier monitoring
- 📊 **Visualizations**: Multi-temporal comparison and change detection maps
- 📈 **Time Series Analysis**: Glacier area trends and melt rate estimation
- 📄 **Automated Reports**: Comprehensive analysis reports in Markdown 

---

## 3. Project Links

- **🚀 Quick Start Checklist**: [QUICK_START_CHECKLIST.md](QUICK_START_CHECKLIST.md) - Get started in 10 minutes
- **🎯 Visual Infographic**: [QUICK_START_INFOGRAPHIC.txt](QUICK_START_INFOGRAPHIC.txt) - Visual quick start guide
- **⚡ One-Liner Guide**: [QUICK_START_ONELINER.txt](QUICK_START_ONELINER.txt) - Ultra-fast reference
- **Quick Start Guide**: [QUICK_START.md](QUICK_START.md) - Get started in 30 minutes
- **🔧 Auto-Start Script**: [start.sh](start.sh) - Automated setup script
- **Polarization Guide**: [POLARIZATION_GUIDE.md](POLARIZATION_GUIDE.md) - Detailed technical reference
- **Debris Classification**: [DEBRIS_CLASSIFICATION.md](DEBRIS_CLASSIFICATION.md) - Solving ice vs rock discrimination
- **ASF API Guide**: [ASF_API_GUIDE.md](ASF_API_GUIDE.md) - Automated data downloading
- **Golubina Workflow**: [GOLUBINA_WORKFLOW.md](GOLUBINA_WORKFLOW.md) - Complete workflow for Golubina Glacier
- **Pipeline Documentation**: [sar_pipeline.py](sar_pipeline.py) - Main processing code
- **Examples**: [example_workflow.py](example_workflow.py) - Working examples 

---

## 4. Project Details

**How it works:**
1. **Automated Data Acquisition**: Download Sentinel-1 SAR data via ASF API (10+ years of data)
2. **Preprocessing**: Radiometric calibration, speckle filtering, terrain correction
3. **Glacier Detection**: Automated boundary detection using backscatter thresholding
4. **Advanced Classification**: Multi-method approach to distinguish ice from debris/rock
5. **Change Detection**: Multi-temporal comparison to identify melting zones
6. **Time Series Analysis**: Calculate melt rates and trends over multiple years
7. **Visualization**: Generate comprehensive maps and graphs
8. **Reporting**: Automated report generation with interpretation and recommendations

**Polarization Choice: VV (Vertical-Vertical)**
- Optimal sensitivity to ice surface changes and melt water
- High contrast between glacier and surrounding terrain
- Best data availability from Sentinel-1
- Proven effectiveness in cryosphere applications  

**Goals:**
- ✅ **Automated data acquisition** via ASF API (10+ years of Sentinel-1 data)
- ✅ Detect glacier boundaries and melting zones using SAR backscatter analysis
- ✅ **Solve ice vs rock discrimination** using multi-method classification approach
- ✅ Quantify melt rates and forecast future changes with time series modeling
- ✅ Assess risks for water resources, floods, and public safety
- ✅ Provide actionable insights for researchers and authorities
- ✅ Create automated pipeline for continuous monitoring

**Technical Implementation:**
- Python-based processing pipeline with modular architecture
- **Automated ASF API integration** for downloading 10+ years of Sentinel-1 data
- Support for Sentinel-1 GRD and SLC products
- Automated preprocessing (calibration, filtering, terrain correction)
- **Advanced surface classification** (ice vs debris using polarization, temporal, and texture analysis)
- Multiple change detection algorithms (differencing, ratio, coherence)
- Machine learning ready for advanced classification
- Comprehensive visualization and reporting tools
- **Time series analysis** for long-term trend detection

---

## 5. Use of AI

  **LLM`s**
- [GitHub Copilot](https://copilot.microsoft.com/) - Coding support  
- [ChatGPT](https://chat.openai.com/) - Research and problem-solving assistance
- [Grok](https://grok.com/) - Research and problem-solving assistance
  
**ML**
- [DinovV3](https://ai.meta.com/dinov3/) - ML for data analysis, forecasting, and computer vision
  
---

## 6. Sources

**NASA sources**

- [Intro to Synthetic Aperture Radar (SAR)](https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar)
- [Alaska Satellite Facility (ASF) Data Search Vertex](https://search.asf.alaska.edu/)
- [SAR StoryMaps](https://nisar.jpl.nasa.gov/applications/arcgis-storymaps/)
**Other sources**
- https://qgis.org - GIS visualization
- https://nakarte.me/ - Topographic maps
- https://www.google.com/maps - Location reference
- ESA SNAP Toolbox - SAR processing software
- Google Earth Engine - Large-scale analysis

**Scientific References**
- Nagler et al. (2015) - Wet snow retrieval with SAR
- Paul et al. (2016) - Glacier Climate Change Initiative
- Winsvold et al. (2018) - SAR for glacier mapping

---

## 7. Installation & Usage

### Quick Installation
```bash
# Clone repository
git clone https://github.com/your-team/GlacierSAR-Kyrgyzstan.git
cd GlacierSAR-Kyrgyzstan

# Install dependencies
pip install -r requirements.txt

# Run example
python example_workflow.py
```

### Basic Usage
```python
from sar_pipeline import SARGlacierPipeline

# Initialize pipeline
pipeline = SARGlacierPipeline('config.yaml')

# Process SAR images
img1 = pipeline.preprocess_sar_image('data/image_2023.tif')
img2 = pipeline.preprocess_sar_image('data/image_2024.tif')

# Compare and visualize
results = pipeline.compare_images(img1, img2, '2023-06-01', '2024-06-01')
pipeline.visualize_comparison(img1, img2, results, 'output.png')
```

See [QUICK_START.md](QUICK_START.md) for detailed instructions.

---

## Team

- **Dmitrii Pecherkin** — Team Lead & Infrastructure Engineer; team organization, project vision, infrastructure setup  
- **Mikhail Vasilyev** — Developer; oversees coding, initial SAR data extraction, analysis, and implementation  
- **Farit Gatiatullin** — Developer; supports SAR data analysis and implementation, contributing research insights 
- **Kenenbek Arzymatov** — Data Scientist; trains and tunes ML models, makes predictions, improves accuracy  
- **Juozas Bechelis** — Contributor; ideas and infrastructure support  

**Team page:** [TengriSpacers on NASA Space Apps Challenge](https://www.spaceappschallenge.org/2025/find-a-team/tengrispacers/)
