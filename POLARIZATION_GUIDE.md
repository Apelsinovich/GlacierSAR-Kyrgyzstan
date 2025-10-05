# SAR Polarization Guide for Glacier Monitoring
## Technical Reference for Ala-Archa Glaciers Project

---

## Executive Summary

**RECOMMENDATION: Use VV polarization for glacier monitoring**

VV (vertical transmission, vertical reception) is the optimal choice for glacier melting analysis in the Ala-Archa project.

---

## 1. Understanding SAR Polarization

### What is polarization?

Polarization defines the orientation of electromagnetic waves:
- **H (Horizontal)** - Horizontal
- **V (Vertical)** - Vertical

### Four main combinations:

1. **HH** - Horizontal transmission, Horizontal reception
2. **HV** - Horizontal transmission, Vertical reception (cross-polarization)
3. **VH** - Vertical transmission, Horizontal reception (cross-polarization)
4. **VV** - Vertical transmission, Vertical reception

---

## 2. Polarization comparison for glaciers

| Polarization | Advantages | Disadvantages | Usage |
|-------------|------------|---------------|-------|
| **VV** ⭐ | • High sensitivity to ice surface<br>• Excellent for melt water detection<br>• Good snow penetration<br>• Sensitive to surface roughness | • May be sensitive to noise<br>• Requires good calibration | **MAIN RECOMMENDATION**<br>Optimal for:<br>- Melting detection<br>- Ablation zone mapping<br>- Glacier boundary definition |
| **HH** | • Good penetration<br>• Sensitive to ice structure<br>• Useful for dry snow | • Less sensitive to melt water<br>• Less data available | **ALTERNATIVE**<br>Useful for:<br>- Dry snow/firn<br>- Structural analysis |
| **HV/VH** | • Sensitive to volume scattering<br>• Useful for surface type classification | • Weak signal from smooth surfaces<br>• Low signal-to-noise ratio for ice | **ADDITIONAL**<br>Use for:<br>- Debris cover<br>- Surface classification |

---

## 3. Why is VV optimal for our project?

### 3.1 Melt water detection
- VV polarization is **most sensitive** to presence of liquid water on glacier surface
- Melt water sharply reduces backscatter in VV
- This allows clear mapping of melting zones

### 3.2 Surface roughness sensitivity
- VV excellently distinguishes:
  - Smooth ice (low backscatter)
  - Rough ice (high backscatter)
  - Wet snow (medium backscatter)

### 3.3 Glacier boundary definition
- VV provides **high contrast** between:
  - Glacier surfaces
  - Surrounding rocks
  - Moraine zones

### 3.4 Time series
- VV has **maximum availability** of Sentinel-1 data
- Allows creating dense time series
- Best data consistency over time

---

## 4. Backscatter characteristics

### Typical σ⁰ (Sigma0) values in dB for VV:

| Surface Type | Backscatter (dB) | Interpretation |
|--------------|------------------|----------------|
| **Dry snow** | -10 to -5 | High backscatter (bright) |
| **Firn** | -12 to -8 | Medium-high |
| **Glacier ice (dry)** | -8 to -3 | High (very bright) |
| **Wet snow/ice** | -18 to -12 | Low (dark) |
| **Melt water on surface** | < -20 | Very low (very dark) |
| **Rocks/moraine** | -5 to 0 | Very high |

### Key melting indicators in VV:
1. **Backscatter decrease** > 3 dB → Likely melting
2. **Temporary decrease** in summer months → Seasonal melting
3. **Persistent decrease** over time → Glacier surface change

---

## 5. When to use other polarizations

### Use HH when:
- Analyzing predominantly dry snow
- Need information about deep structure
- VV data unavailable

### Use HV/VH when:
- Mapping debris cover on glacier
- Conducting detailed surface classification
- Need information about volume scattering

### Use full polarimetry (Quad-pol) when:
- Need maximum detailed information
- Conducting scientific research with high requirements
- Resources available for complex processing
- **BUT**: data less available and requires more processing

---

## 6. Practical recommendations for Ala-Archa

### Data strategy:

#### Minimal configuration (recommended for competition):
```yaml
Polarization: VV
Satellite: Sentinel-1
Product type: GRD (Ground Range Detected)
Mode: IW (Interferometric Wide)
Orbit: ASCENDING or DESCENDING (one for all)
Temporal interval: 12 days (Sentinel-1 repeat cycle)
```

#### Extended configuration (if time allows):
```yaml
Main polarization: VV
Additional: VH (if available in dual-pol products)
Can use: VV/VH ratio for better classification
```

### Temporal periods for analysis:

1. **Winter baseline period** (January-March):
   - Minimal melting
   - Establish baseline for comparison

2. **Active melting period** (June-August):
   - Maximum changes
   - Key period for melting detection

3. **Inter-annual comparison**:
   - Compare same months of different years
   - For example: July 2020 vs July 2024

---

## 7. Data download

### Alaska Satellite Facility (ASF) - Recommended

**Steps:**
1. Go to https://search.asf.alaska.edu/
2. Select area of interest (Ala-Archa: 42.5°N, 74.5°E)
3. Filters:
   - Dataset: Sentinel-1
   - Beam Mode: IW
   - Polarization: **VV** or **VV+VH** (dual-pol)
   - Product Type: GRD_HD or GRD_MD
4. Select dates
5. Download

### Alternative sources:
- **Copernicus Open Access Hub**: https://scihub.copernicus.eu/
- **Google Earth Engine**: For automated processing
- **ESA SNAP Toolbox**: For local processing

---

## 8. Processing in pipeline

### Using our pipeline:

```python
from sar_pipeline import SARGlacierPipeline

# Initialize
pipeline = SARGlacierPipeline('config.yaml')

# Process VV polarization
vv_image = pipeline.preprocess_sar_image(
    'raw_data/S1A_IW_GRDH_VV_20240601.tif',
    'preprocessed/image_20240601_VV.tif'
)

# Glacier detection
glacier_mask = pipeline.detect_glacier_boundaries(vv_image)

# Compare temporal points
results = pipeline.compare_images(
    vv_image_2023, vv_image_2024,
    '2023-06-01', '2024-06-01'
)
```

---

## 9. Results interpretation

### What changes in VV show:

#### Backscatter decrease (blue areas on change map):
✓ **Likely**: Snow/ice melting  
✓ **Likely**: Increased moisture  
✓ **Likely**: Dry→wet snow transition  
✗ **Unlikely**: New snow accumulation

#### Backscatter increase (red areas):
✓ **Likely**: Melt water freezing  
✓ **Likely**: Increased roughness  
✓ **Likely**: Dry snowfall  
✗ **Unlikely**: Melting

---

## 10. Validation and quality control

### Check your results:

1. **Seasonal consistency**:
   - Summer should show more backscatter decrease
   - Winter - increase or stability

2. **Geographic consistency**:
   - Changes should correspond to known glaciers
   - No changes should occur on rocks

3. **Comparison with optical data**:
   - Use Landsat/Sentinel-2 for validation
   - Cloudiness can be a problem

4. **Climate data**:
   - Check against temperature trends
   - Correlate with precipitation

---

## 11. Frequently asked questions

**Q: Can VV and HH be combined?**  
A: Yes, if both are available. But usually for Sentinel-1, VV+VH (dual-pol) is available.

**Q: What is better: GRD or SLC?**  
A: For initial analysis use **GRD** (simpler). SLC is needed for interferometry.

**Q: What is the spatial resolution of VV Sentinel-1?**  
A: GRD products: 10m x 10m (after processing)

**Q: How much data should be downloaded?**  
A: For presentation, 4-6 scenes are sufficient (2-3 dates, possibly different years)

**Q: Can other SAR satellites be used?**  
A: Yes (ALOS-2, RADARSAT-2, TerraSAR-X), but Sentinel-1 is free and available.

---

## 12. Competition summary

### Your polarization choice: **VV** ✅

### Justification for presentation:

> "We chose VV polarization Sentinel-1 SAR for monitoring Ala-Archa glaciers because:
> 
> 1. **Optimal sensitivity** to melt water and ice surface changes
> 2. **High contrast** between glacier and non-glacier surfaces
> 3. **Maximum data availability** for creating dense time series
> 4. **Proven effectiveness** in scientific literature for cryospheric applications
> 
> VV polarization allows us to reliably detect active melting zones and quantitatively assess glacier area changes over time."

---

## 13. Additional resources

### Scientific literature:
- Nagler et al. (2015) - "Retrieval of wet snow by means of multitemporal SAR data"
- Winsvold et al. (2018) - "Using SAR for glacier mapping in Norway"
- Paul et al. (2016) - "The glaciers climate change initiative: Methods for glacier monitoring"

### Online courses:
- NASA ARSET - SAR for Land Applications
- ESA RUS Training - SAR Basics

### Tools:
- ESA SNAP - Free SAR processor
- QGIS - Visualization
- Python + GDAL - Automation

---

**Document prepared for Team TengriSpacers**  
**NASA Space Apps Challenge 2025**  
**Project: Through the Radar Looking Glass - Ala-Archa Glaciers**


