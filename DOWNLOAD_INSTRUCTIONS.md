# 🏔️ Instructions for downloading Golubina Glacier images

## ✅ What was done

Created improved script `download_glacier_auto.py` that:
- 🔍 Finds SAR images of Sentinel-1 for Golubina Glacier
- 📅 Selects images for July each year (melting peak)
- 📡 Uses VV+VH polarization for better analysis
- 💾 Shows details of all found files

## 📋 Found images

**Total found: 9 images (2017-2025)**

| Year | Date | Size | Filename |
|------|------|------|----------|
| 2017 | 2017-07-17 | 0.94 GB | S1A_IW_GRDH_1SDV_20170717T010448_20170717T010513_017504_01D43E_3C44.zip |
| 2018 | 2018-07-17 | 0.92 GB | S1A_IW_GRDH_1SDV_20180717T011256_20180717T011321_022827_02799C_E74A.zip |
| 2019 | 2019-07-13 | 0.88 GB | S1A_IW_GRDH_1SDV_20190713T125911_20190713T125936_028099_032C6A_BCAE.zip |
| 2020 | 2020-07-14 | 0.89 GB | S1A_IW_GRDH_1SDV_20200714T125107_20200714T125132_033451_03E055_1217.zip |
| 2021 | 2021-07-14 | 0.83 GB | S1A_IW_GRDH_1SDV_20210714T125923_20210714T125948_038774_049348_C3FA.zip |
| 2022 | 2022-07-15 | 0.89 GB | S1A_IW_GRDH_1SDV_20220715T010519_20220715T010544_044104_0543B1_D594.zip |
| 2023 | 2023-07-15 | 0.90 GB | S1A_IW_GRDH_1SDV_20230715T011326_20230715T011351_049427_05F18F_E557.zip |
| 2024 | 2024-07-16 | 0.91 GB | S1A_IW_GRDH_1SDV_20240716T010523_20240716T010548_054779_06AB98_5CFF.zip |
| 2025 | 2025-07-16 | 0.90 GB | S1A_IW_GRDH_1SDV_20250716T011316_20250716T011341_060102_0777B6_27F7.zip |

**Total size: 8.06 GB**

## 🚀 Using the script

### 1. Search available images (without download)

```bash
# Show all available images
python3 download_glacier_auto.py

# Limit number of images
python3 download_glacier_auto.py --max 5

# Set time range
python3 download_glacier_auto.py --start-year 2020 --end-year 2023
```

### 2. Automatic download (requires NASA account)

```bash
# Download all found files
python3 download_glacier_auto.py --download

# Download only last 3 years
python3 download_glacier_auto.py --download --start-year 2023 --end-year 2025 --max 3
```

### 3. Command line parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--download` | Start automatic download | false (search only) |
| `--start-year` | Start year | 2015 |
| `--end-year` | End year | 2025 |
| `--max` | Maximum images | 10 |

## 📥 Download methods

### Option 1: Automatic download via script

**Requirements:**
1. NASA Earthdata account: https://urs.earthdata.nasa.gov/users/new
2. Configure credentials (one of methods):
   - Via `.netrc` file in home directory
   - Via environment variables
   - Interactive input on first request

**Command:**
```bash
python3 download_glacier_auto.py --download --max 9
```

### Option 2: Manual download via web interface

1. Open: https://search.asf.alaska.edu/
2. Enter search parameters:
   - **Platform**: Sentinel-1
   - **Processing Level**: GRD_HD
   - **Start Date**: 2017-07-01
   - **End Date**: 2025-07-31
   - **Geographic Search**: Vertex (draw glacier area)
   - **Coordinates**: 74.5, 42.56 - 74.52, 42.58

3. Download files from list above

4. Save to: `output/raw_data/`

## 📁 Directory structure

After downloading files will be saved:
```
GlacierSAR-Kyrgyzstan/
├── output/
│   └── raw_data/
│       ├── S1A_IW_GRDH_1SDV_20170717T010448_..._.zip
│       ├── S1A_IW_GRDH_1SDV_20180717T011256_..._.zip
│       └── ... (other files)
```

## 🔍 Technical details

### Image parameters:
- **Satellite**: Sentinel-1A
- **Mode**: IW (Interferometric Wide Swath)
- **Polarization**: VV+VH (dual-pol)
- **Processing level**: GRD High Resolution
- **Format**: ZIP archives with GeoTIFF inside

### Area of interest:
- **Glacier**: Golubina (Ala-Archa Gorge)
- **Coordinates**: 74.5°E - 74.52°E, 42.56°N - 42.58°N
- **Country**: Kyrgyzstan

### Time period:
- **Month**: July (summer melting peak)
- **Years**: 2017-2025 (9 years)
- **Interval**: 1 image per year

## 📊 Next steps

After downloading images:

1. **Process data**:
   ```bash
   python3 sar_pipeline.py
   ```

2. **Time series analysis**:
   ```bash
   python3 time_series_processor.py
   ```

3. **Full pipeline**:
   ```bash
   python3 run_full_pipeline.py
   ```

## 🆘 Troubleshooting

### ASF API connection error
- Check internet connection
- Try using VPN
- ASF API may be temporarily unavailable

### Authentication error
1. Register: https://urs.earthdata.nasa.gov/users/new
2. Create `.netrc` file in home directory:
   ```
   machine urs.earthdata.nasa.gov
   login YOUR_USERNAME
   password YOUR_PASSWORD
   ```
3. Set permissions: `chmod 600 ~/.netrc`

### No images for certain years
- 2015-2016: Sentinel-1 just started, limited coverage
- Try expanding search period: `--start-year 2014 --end-year 2026`

## 📖 Additional resources

- **ASF Data Search**: https://search.asf.alaska.edu/
- **ASF API Docs**: https://docs.asf.alaska.edu/api/
- **Sentinel-1 Info**: https://sentinel.esa.int/web/sentinel/missions/sentinel-1
- **Python library**: https://github.com/asfadmin/Discovery-asf_search

---

**Created for NASA Space Apps Challenge 2025**  
**Team: TengriSpacers**  
**Project: GlacierSAR-Kyrgyzstan**
