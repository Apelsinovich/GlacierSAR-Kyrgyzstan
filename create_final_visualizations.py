#!/usr/bin/env python3
"""
Создание финальных визуализаций для ледника Голубина
На основе правильного анализа dB Distribution с точными координатами
"""

import numpy as np
import rasterio
import rasterio.transform
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from scipy.ndimage import median_filter

print("=" * 80)
print("📊 СОЗДАНИЕ ФИНАЛЬНЫХ ВИЗУАЛИЗАЦИЙ")
print("=" * 80)

# Загружаем результаты
with open('output/results/glacier_golubina_FINAL_PRECISE.json', 'r') as f:
    results = json.load(f)

print(f"\n✅ Загружено результатов: {len(results)}")
print(f"   (2020 год исключен - испорченные данные)\n")

# Параметры
TARGET_LON = (74.460, 74.520)
TARGET_LAT = (42.440, 42.500)
CALIB_FACTOR = 52.7
GLACIER_PERCENTILE = 33.3

def get_geolocation_grid(xml_path):
    """Извлекает геолокационную сетку из XML"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        gcps = []
        for point in root.findall('.//{*}geolocationGridPoint'):
            try:
                pixel = int(point.find('./{*}pixel').text)
                line = int(point.find('./{*}line').text)
                lat = float(point.find('./{*}latitude').text)
                lon = float(point.find('./{*}longitude').text)
                
                gcps.append(rasterio.control.GroundControlPoint(
                    row=line, col=pixel, x=lon, y=lat
                ))
            except (AttributeError, ValueError, TypeError):
                continue
        
        return gcps if gcps else None
    except Exception:
        return None

def lonlat_to_pixel_precise(lon, lat, gcps, img_width, img_height):
    """Точная конвертация lon/lat в pixel используя GCP"""
    try:
        transform = rasterio.transform.from_gcps(gcps)
        row, col = rasterio.transform.rowcol(transform, lon, lat)
        col = int(np.clip(col, 0, img_width - 1))
        row = int(np.clip(row, 0, img_height - 1))
        return col, row
    except Exception:
        return None, None

def calibrate_to_sigma0(data, factor):
    return 10 * np.log10((data.astype(float) ** 2) + 1e-10) - factor

def find_glacier_simple(data_db, percentile=33.3):
    data_filtered = median_filter(data_db, size=3)
    valid = np.isfinite(data_filtered)
    threshold = np.percentile(data_filtered[valid], percentile)
    glacier_mask = (data_filtered <= threshold) & valid
    return glacier_mask, threshold

# === ВИЗУАЛИЗАЦИЯ 1: Графики изменений ===
print("\n📊 Создание графиков изменений...")

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

years = [r['year'] for r in results]
areas = [r['glacier_area_km2'] for r in results]
backscatter = [r['mean_backscatter'] for r in results]
coverage = [r['coverage_percent'] for r in results]

# График 1: Площадь
ax1.plot(years, areas, 'o-', linewidth=3, markersize=10, color='#2E86AB', label='Площадь ледника')
ax1.fill_between(years, areas, alpha=0.3, color='#2E86AB')
ax1.axhline(y=np.mean(areas), color='red', linestyle='--', linewidth=2, label=f'Среднее: {np.mean(areas):.2f} км²')
ax1.set_xlabel('Год', fontsize=14, fontweight='bold')
ax1.set_ylabel('Площадь (км²)', fontsize=14, fontweight='bold')
ax1.set_title('Площадь ледника Голубина (2017-2025)\nGlacier Ice (33.3% перцентиль)', 
             fontsize=16, fontweight='bold', pad=20)
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(fontsize=12, loc='upper right')

# Аннотации
for year, area in zip(years, areas):
    ax1.annotate(f'{area:.2f}',
                xy=(year, area),
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))

# График 2: Backscatter
ax2.plot(years, backscatter, 's-', linewidth=3, markersize=10, color='#A23B72', label='Mean Sigma0')
ax2.fill_between(years, backscatter, alpha=0.3, color='#A23B72')
ax2.set_xlabel('Год', fontsize=14, fontweight='bold')
ax2.set_ylabel('Sigma0 (dB)', fontsize=14, fontweight='bold')
ax2.set_title('Backscatter ледника', fontsize=14, fontweight='bold', pad=15)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=12)

# График 3: Изменения относительно 2017
base_area = areas[0]
changes = [(a - base_area) / base_area * 100 for a in areas]
colors = ['green' if c >= 0 else 'red' for c in changes]

bars = ax3.bar(years, changes, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
ax3.set_xlabel('Год', fontsize=14, fontweight='bold')
ax3.set_ylabel('Изменение (%)', fontsize=14, fontweight='bold')
ax3.set_title(f'Изменение площади относительно 2017 года', fontsize=14, fontweight='bold', pad=15)
ax3.axhline(y=0, color='black', linestyle='-', linewidth=2)
ax3.grid(True, alpha=0.3, linestyle='--', axis='y')

# Значения на столбцах
for year, change, bar in zip(years, changes, bars):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
            f'{change:+.1f}%',
            ha='center',
            va='bottom' if change > 0 else 'top',
            fontsize=10,
            fontweight='bold')

plt.tight_layout()
output1 = Path("output/visualizations/glacier_dynamics_FINAL.png")
output1.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output1, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ Сохранено: {output1.name}")
plt.close()

# === ВИЗУАЛИЗАЦИЯ 2: SAR снимки по годам ===
print("\n📸 Создание SAR снимков по годам...")

data_dir = Path("output/raw_data")
safe_dirs = sorted(list(data_dir.glob("*.SAFE")))
vv_files = sorted(list(data_dir.glob("**/*vv*.tiff")))

# Выбираем ключевые годы для визуализации
key_years = [2017, 2019, 2022, 2025]
glacier_images = []

for safe_dir, vv_file in zip(safe_dirs, vv_files):
    date_str = vv_file.stem.split('-')[4][:8]
    date = datetime.strptime(date_str, '%Y%m%d')
    year = date.year
    
    if year not in key_years or year == 2020:  # Исключаем 2020
        continue
    
    try:
        # Используем XML для точных координат
        xml_files = list(safe_dir.glob("**/s1*vv*.xml"))
        if not xml_files:
            print(f"   {year}: ❌ XML не найден")
            continue
        
        gcps = get_geolocation_grid(xml_files[0])
        if not gcps or len(gcps) < 4:
            print(f"   {year}: ❌ GCP не найдены")
            continue
        
        with rasterio.open(vv_file) as src:
            img_width = src.width
            img_height = src.height
            
            corners_lonlat = [
                (TARGET_LON[0], TARGET_LAT[0]),
                (TARGET_LON[1], TARGET_LAT[0]),
                (TARGET_LON[1], TARGET_LAT[1]),
                (TARGET_LON[0], TARGET_LAT[1])
            ]
            
            pixels_x = []
            pixels_y = []
            
            for lon, lat in corners_lonlat:
                px, py = lonlat_to_pixel_precise(lon, lat, gcps, img_width, img_height)
                if px is None:
                    raise ValueError("Конвертация координат не удалась")
                pixels_x.append(px)
                pixels_y.append(py)
            
            pixel_min = max(0, min(pixels_x))
            pixel_max = min(img_width, max(pixels_x))
            line_min = max(0, min(pixels_y))
            line_max = min(img_height, max(pixels_y))
            
            region_data = src.read(1, window=((line_min, line_max), (pixel_min, pixel_max)))
            region_db = calibrate_to_sigma0(region_data, CALIB_FACTOR)
            
            glacier_mask, threshold = find_glacier_simple(region_db, GLACIER_PERCENTILE)
            
            # Находим статистику для этого года
            year_stats = next((r for r in results if r['year'] == year), None)
            
            glacier_images.append({
                'year': year,
                'date': date.strftime('%Y-%m-%d'),
                'data_db': region_db,
                'glacier_mask': glacier_mask,
                'stats': year_stats,
                'threshold': threshold
            })
            
            print(f"   {year}: загружено")
            
    except Exception as e:
        print(f"   {year}: ошибка - {e}")

# Создаем визуализацию
if glacier_images:
    n = len(glacier_images)
    fig = plt.figure(figsize=(6*n, 15))
    
    for idx, img in enumerate(glacier_images):
        # Ряд 1: Оригинальный SAR
        ax1 = plt.subplot(3, n, idx + 1)
        im1 = ax1.imshow(img['data_db'], cmap='gray', vmin=-25, vmax=5)
        ax1.set_title(f"{img['year']}\nSAR Sigma0 (VV)", fontsize=14, fontweight='bold')
        ax1.axis('off')
        plt.colorbar(im1, ax=ax1, label='dB', fraction=0.046, pad=0.04)
        
        # Ряд 2: Цветная карта
        ax2 = plt.subplot(3, n, idx + 1 + n)
        im2 = ax2.imshow(img['data_db'], cmap='RdYlBu_r', vmin=-25, vmax=5)
        ax2.set_title(f"Цветная карта\nпорог: {img['threshold']:.1f} dB", fontsize=12, fontweight='bold')
        ax2.axis('off')
        plt.colorbar(im2, ax=ax2, label='dB', fraction=0.046, pad=0.04)
        
        # Ряд 3: Маска ледника
        ax3 = plt.subplot(3, n, idx + 1 + 2*n)
        
        # RGB с выделением ледника
        rgb = np.zeros((*img['data_db'].shape, 3))
        normalized = (img['data_db'] + 25) / 30
        normalized = np.clip(normalized, 0, 1)
        rgb[:,:,0] = normalized
        rgb[:,:,1] = normalized
        rgb[:,:,2] = normalized
        
        # Ледник выделяем синим
        rgb[img['glacier_mask'], 0] = 0.1
        rgb[img['glacier_mask'], 1] = 0.6
        rgb[img['glacier_mask'], 2] = 1.0
        
        ax3.imshow(rgb)
        if img['stats']:
            ax3.set_title(f"Glacier Ice\nПлощадь: {img['stats']['glacier_area_km2']:.2f} км²",
                         fontsize=11, fontweight='bold')
        ax3.axis('off')
    
    plt.suptitle('Ледник Голубина: Временная динамика (Sentinel-1A VV)\n'
                 'Glacier Ice определен как 33.3% перцентиль backscatter',
                fontsize=16, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    output2 = Path("output/visualizations/glacier_timeline_FINAL.png")
    plt.savefig(output2, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Сохранено: {output2.name}")
    plt.close()

# === ВИЗУАЛИЗАЦИЯ 3: Сравнение 2017 vs 2025 ===
if len(glacier_images) >= 2:
    print("\n🔍 Создание детального сравнения...")
    
    first = glacier_images[0]
    last = glacier_images[-1]
    
    fig = plt.figure(figsize=(20, 10))
    
    # 2017
    ax1 = plt.subplot(2, 4, 1)
    im1 = ax1.imshow(first['data_db'], cmap='gray', vmin=-25, vmax=5)
    ax1.set_title(f"{first['year']} - SAR Sigma0", fontsize=14, fontweight='bold')
    ax1.axis('off')
    plt.colorbar(im1, ax=ax1, label='dB', fraction=0.046)
    
    ax2 = plt.subplot(2, 4, 2)
    im2 = ax2.imshow(first['data_db'], cmap='RdYlBu_r', vmin=-25, vmax=5)
    ax2.set_title(f"{first['year']} - Цветная карта", fontsize=14, fontweight='bold')
    ax2.axis('off')
    plt.colorbar(im2, ax=ax2, label='dB', fraction=0.046)
    
    # 2025
    ax3 = plt.subplot(2, 4, 3)
    im3 = ax3.imshow(last['data_db'], cmap='gray', vmin=-25, vmax=5)
    ax3.set_title(f"{last['year']} - SAR Sigma0", fontsize=14, fontweight='bold')
    ax3.axis('off')
    plt.colorbar(im3, ax=ax3, label='dB', fraction=0.046)
    
    ax4 = plt.subplot(2, 4, 4)
    im4 = ax4.imshow(last['data_db'], cmap='RdYlBu_r', vmin=-25, vmax=5)
    ax4.set_title(f"{last['year']} - Цветная карта", fontsize=14, fontweight='bold')
    ax4.axis('off')
    plt.colorbar(im4, ax=ax4, label='dB', fraction=0.046)
    
    # Нижний ряд
    ax5 = plt.subplot(2, 4, 5)
    rgb1 = np.zeros((*first['data_db'].shape, 3))
    norm1 = (first['data_db'] + 25) / 30
    norm1 = np.clip(norm1, 0, 1)
    rgb1[:,:,:] = norm1[:,:,np.newaxis]
    rgb1[first['glacier_mask'], :] = [0.1, 0.6, 1.0]
    ax5.imshow(rgb1)
    ax5.set_title(f"{first['year']} - Glacier Ice\n{first['stats']['glacier_area_km2']:.2f} км²",
                 fontsize=12, fontweight='bold')
    ax5.axis('off')
    
    ax6 = plt.subplot(2, 4, 6)
    rgb2 = np.zeros((*last['data_db'].shape, 3))
    norm2 = (last['data_db'] + 25) / 30
    norm2 = np.clip(norm2, 0, 1)
    rgb2[:,:,:] = norm2[:,:,np.newaxis]
    rgb2[last['glacier_mask'], :] = [0.1, 0.6, 1.0]
    ax6.imshow(rgb2)
    ax6.set_title(f"{last['year']} - Glacier Ice\n{last['stats']['glacier_area_km2']:.2f} км²",
                 fontsize=12, fontweight='bold')
    ax6.axis('off')
    
    # Разница backscatter - используем меньший размер
    ax7 = plt.subplot(2, 4, 7)
    min_h = min(first['data_db'].shape[0], last['data_db'].shape[0])
    min_w = min(first['data_db'].shape[1], last['data_db'].shape[1])
    diff_backscatter = last['data_db'][:min_h, :min_w] - first['data_db'][:min_h, :min_w]
    im7 = ax7.imshow(diff_backscatter, cmap='RdBu_r', vmin=-10, vmax=10)
    ax7.set_title(f"Δ Backscatter\n{first['year']} → {last['year']}",
                 fontsize=12, fontweight='bold')
    ax7.axis('off')
    plt.colorbar(im7, ax=ax7, label='Δ dB', fraction=0.046)
    
    # Карта изменений - используем меньший размер
    ax8 = plt.subplot(2, 4, 8)
    change_map = np.zeros((min_h, min_w))
    first_mask_crop = first['glacier_mask'][:min_h, :min_w]
    last_mask_crop = last['glacier_mask'][:min_h, :min_w]
    change_map[first_mask_crop & ~last_mask_crop] = -1
    change_map[~first_mask_crop & last_mask_crop] = 1
    
    rgb_change = np.zeros((min_h, min_w, 3))
    norm1_crop = norm1[:min_h, :min_w]
    rgb_change[:,:,0] = norm1_crop
    rgb_change[:,:,1] = norm1_crop
    rgb_change[:,:,2] = norm1_crop
    rgb_change[change_map == -1, :] = [1.0, 0.2, 0.2]
    rgb_change[change_map == 1, :] = [0.2, 1.0, 0.2]
    rgb_change[(first_mask_crop & last_mask_crop), :] = [0.1, 0.6, 1.0]
    
    ax8.imshow(rgb_change)
    
    area_change = last['stats']['glacier_area_km2'] - first['stats']['glacier_area_km2']
    pct_change = (area_change / first['stats']['glacier_area_km2']) * 100
    
    ax8.set_title(f"Изменения площади\n{area_change:+.2f} км² ({pct_change:+.1f}%)",
                 fontsize=12, fontweight='bold')
    ax8.axis('off')
    
    # Легенда
    red_patch = mpatches.Patch(color='red', label='Потери')
    green_patch = mpatches.Patch(color='green', label='Прирост')
    blue_patch = mpatches.Patch(color='cyan', label='Стабильно')
    fig.legend(handles=[red_patch, green_patch, blue_patch],
              loc='lower center', ncol=3, fontsize=14, frameon=True, fancybox=True)
    
    plt.suptitle(f'Детальное сравнение: {first["year"]} vs {last["year"]}\n'
                f'Ледник Голубина, Ala-Archa Gorge, Kyrgyzstan',
                fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    
    output3 = Path("output/visualizations/glacier_comparison_FINAL.png")
    plt.savefig(output3, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Сохранено: {output3.name}")
    plt.close()

print(f"\n{'=' * 80}")
print(f"✅ ВСЕ ВИЗУАЛИЗАЦИИ СОЗДАНЫ")
print(f"{'=' * 80}\n")

