# ASF API Guide: Automated Sentinel-1 Data Download

## 🚀 Quick start

```bash
# 1. Install dependencies
pip3 install requests

# 2. Download 10 years of data for Golubina Glacier
python3 asf_api_downloader.py --years 2015 2025 --month 7

# 3. Or run the full pipeline automatically
python3 run_full_pipeline.py
```

---

## 📋 ASF API Parameters

### Main search parameters:

| Parameter | Description | Example value |
|-----------|-------------|---------------|
| `platform` | Satellite platform | `"Sentinel-1"` |
| `processingLevel` | Processing level | `"GRD_HD"` |
| `beamMode` | Acquisition mode | `"IW"` |
| `polarization` | Polarization | `"VV+VH"` |
| `start` | Start date | `"2015-07-01"` |
| `end` | End date | `"2025-07-31"` |
| `bbox` | Area boundaries | `"74.5,42.56,74.52,42.58"` |

### Configuration for Golubina Glacier:

```yaml
# config.yaml
api_download:
  target_glacier_bbox:
    min_lon: 74.5000
    min_lat: 42.5600
    max_lon: 74.5200
    max_lat: 42.5800

  start_year: 2015
  end_year: 2025
  target_month: 7  # July - melting peak
  polarization: "VV+VH"
  max_downloads: 15
```

---

## 🗓️ Scanning strategy

### Annual summer images:

```python
# Download one image per July each year
for year in range(2015, 2026):
    start_date = f"{year}-06-15"
    end_date = f"{year}-08-15"

    # Find the best image in this period
    granules = search_granules(bbox, start_date, end_date)
    best_granule = select_best_annual_scene(granules, target_month=7)
    download_granule(best_granule)
```

### Advantages of this approach:
- ✅ One image per year at melting season peak
- ✅ Minimal data volume (10-15 files)
- ✅ Sufficient for 10-year trend analysis
- ✅ Focus on summer period (maximum melting)

---

## 🔧 Usage examples

### Example 1: Download for specific glacier

```python
from asf_api_downloader import ASFAPIDownloader

# Initialize
downloader = ASFAPIDownloader()

# Golubina Glacier coordinates
bbox = (74.5000, 42.5600, 74.5200, 42.5800)

# Download for 10 years
downloaded_files = downloader.download_time_series(
    bbox=bbox,
    start_year=2015,
    end_year=2025,
    target_month=7,  # July
    polarization="VV+VH"
)
```

### Example 2: Custom parameters

```python
# Download for different region/period
custom_files = downloader.download_time_series(
    bbox=(74.45, 42.55, 74.55, 42.65),  # Different region
    start_year=2020,
    end_year=2023,
    target_month=8,  # August
    polarization="VV",
    max_downloads=5
)
```

### Example 3: Test download

```python
# Small test to check functionality
test_files = downloader.download_time_series(
    bbox=(74.50, 42.56, 74.52, 42.58),  # Very small area
    start_year=2022,
    end_year=2023,
    target_month=7,
    polarization="VV",
    max_downloads=2  # Only 2 files
)
```

---

## 📊 ASF API Response Structure

### Example search response:

```json
{
  "results": [
    {
      "sceneDate": "2023-07-15",
      "platform": "Sentinel-1",
      "beamMode": "IW",
      "polarization": "VV+VH",
      "downloadUrl": "https://...",
      "fileName": "S1A_IW_GRDH_1SDV_20230715T...zip",
      "sizeMB": 850.5,
      "footprint": "POLYGON((74.45 42.55, 74.55 42.55, ...))"
    }
  ]
}
```

### Key fields:
- `sceneDate`: Acquisition date
- `downloadUrl`: Direct download link
- `polarization`: Available polarizations
- `sizeMB`: File size in MB

---

## 🚨 Important notes

### ASF API limitations:
- **Free** for scientific purposes
- **Request limit**: ~1000 per hour (to prevent abuse)
- **File size**: Sentinel-1 GRD ~800-900 MB each
- **Download time**: 1-2 minutes per file (depends on internet speed)

### Error handling:

```python
try:
    granules = downloader.search_granules(bbox, start_date, end_date)
    if not granules:
        print("❌ No data found for specified period")
        return

    downloaded = downloader.download_time_series(...)
    print(f"✅ Downloaded {len(downloaded)} files")

except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
```

### Recommendations:
1. **Start with test download** of small area
2. **Use VPN** if there are access issues
3. **Check ASF limits** for intensive use

---

## 🎯 For your project

### Golubina Glacier (Ala-Archa):

```bash
# Recommended command for your project:
python3 asf_api_downloader.py --years 2015 2025 --month 7

# This will download:
# • 2015-07: S1A_IW_GRDH_1SDV_201507xx_VV_VH.zip
# • 2016-07: S1A_IW_GRDH_1SDV_201607xx_VV_VH.zip
# • ... (one file per year)
# • 2025-07: S1A_IW_GRDH_1SDV_202507xx_VV_VH.zip
```

### Expected results:
- 📁 **11 files** (2015-2025)
- 📊 **~10 GB** data
- ⏱️ **15-20 minutes** download time
- 🎯 **Ready data** for time series analysis

---

## 🔗 Useful links

- **ASF API documentation**: https://docs.asf.alaska.edu/api/
- **ASF search interface**: https://search.asf.alaska.edu/
- **Sentinel-1 information**: https://sentinel.esa.int/web/sentinel/missions/sentinel-1

---

## ✅ Final recommendations

1. **Use ASF API** for automation
2. **Start with test download** of small area
3. **Download VV+VH polarization** for better classification
4. **Choose July** for melting peak analysis
5. **Limit number** of files to reasonable limits

**Result**: Fully automated 10-year data collection for Golubina Glacier melting analysis! 🚀

---

**Team TengriSpacers** | **NASA Space Apps Challenge 2025**

