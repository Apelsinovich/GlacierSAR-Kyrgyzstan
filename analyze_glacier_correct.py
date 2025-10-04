#!/usr/bin/env python3
"""
ПРАВИЛЬНЫЙ анализ ледника Голубина с реальными данными
Использует пиксельные координаты вместо географических
"""

import numpy as np
import rasterio
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from pathlib import Path
import json
from scipy.ndimage import binary_opening, binary_closing, median_filter

print("=" * 80)
print("🏔️  АНАЛИЗ ЛЕДНИКА ГОЛУБИНА (исправленная версия)")
print("    С реальными SAR снимками")
print("=" * 80)

# Находим все VV файлы
data_dir = Path("output/raw_data")
vv_files = sorted(list(data_dir.glob("**/*vv*.tiff")))

print(f"\n📊 Найдено файлов: {len(vv_files)}")

# Создаем директории
viz_dir = Path("output/visualizations")
results_dir = Path("output/results")
viz_dir.mkdir(parents=True, exist_ok=True)
results_dir.mkdir(parents=True, exist_ok=True)

def extract_region(data, center_x=None, center_y=None, size=1500):
    """Извлекает область из центра изображения"""
    h, w = data.shape
    
    if center_x is None:
        center_x = w // 2
    if center_y is None:
        center_y = h // 2
    
    half_size = size // 2
    
    top = max(0, center_y - half_size)
    bottom = min(h, center_y + half_size)
    left = max(0, center_x - half_size)
    right = min(w, center_x + half_size)
    
    return data[top:bottom, left:right], (top, bottom, left, right)

def segment_ice_area(data_db, threshold=-15):
    """
    Сегментирует ледниковую область
    Используем более низкий порог для лучшего выделения
    """
    # Применяем медианный фильтр для уменьшения шума
    data_filtered = median_filter(data_db, size=3)
    
    # Маска для высоких значений (сухой лед/снег)
    ice_mask = data_filtered > threshold
    
    # Морфологическая обработка
    ice_mask = binary_opening(ice_mask, structure=np.ones((5,5)))
    ice_mask = binary_closing(ice_mask, structure=np.ones((7,7)))
    
    return ice_mask

print("\n🔬 Анализ данных...")
results = []
glacier_images = []

# Ключевые годы для визуализации
key_years = [2017, 2020, 2024, 2025]

for i, vv_file in enumerate(vv_files, 1):
    date_str = vv_file.stem.split('-')[4][:8]
    date = datetime.strptime(date_str, '%Y%m%d')
    year = date.year
    
    print(f"\n[{i}/{len(vv_files)}] {year}: {date.strftime('%Y-%m-%d')}")
    
    try:
        with rasterio.open(vv_file) as src:
            # Читаем полное изображение
            full_data = src.read(1)
            print(f"   📐 Размер: {full_data.shape}")
            
            # Извлекаем центральную область (предположительно там ледник)
            region, bounds = extract_region(full_data, size=1500)
            print(f"   📍 Область: {bounds}")
            
            # Конвертируем в dB
            region_db = 10 * np.log10(region.astype(float) + 1e-10)
            
            # Проверяем статистику
            valid = np.isfinite(region_db)
            print(f"   📊 Backscatter: {np.mean(region_db[valid]):.2f} dB "
                  f"({np.min(region_db[valid]):.2f} - {np.max(region_db[valid]):.2f})")
            
            # Сегментируем ледник
            ice_mask = segment_ice_area(region_db, threshold=-15)
            
            # Рассчитываем площадь
            pixel_area = 10 * 10  # м² (разрешение ~10м для Sentinel-1 GRD)
            ice_pixels = np.sum(ice_mask)
            ice_area_km2 = (ice_pixels * pixel_area) / 1e6
            
            # Статистика по ледниковой области
            ice_backscatter = region_db[ice_mask]
            ice_backscatter = ice_backscatter[np.isfinite(ice_backscatter)]
            
            if len(ice_backscatter) > 100:
                stats = {
                    'year': year,
                    'date': date.strftime('%Y-%m-%d'),
                    'ice_area_km2': float(ice_area_km2),
                    'ice_pixels': int(ice_pixels),
                    'mean_backscatter': float(np.mean(ice_backscatter)),
                    'std_backscatter': float(np.std(ice_backscatter)),
                    'coverage_percent': float(ice_pixels / ice_mask.size * 100),
                    'backscatter_min': float(np.min(ice_backscatter)),
                    'backscatter_max': float(np.max(ice_backscatter))
                }
                
                results.append(stats)
                
                print(f"   ✅ Площадь льда: {ice_area_km2:.2f} км²")
                print(f"   📈 Покрытие: {stats['coverage_percent']:.1f}%")
                
                # Сохраняем для визуализации
                if year in key_years:
                    glacier_images.append({
                        'year': year,
                        'date': date.strftime('%Y-%m-%d'),
                        'data_db': region_db,
                        'ice_mask': ice_mask,
                        'stats': stats
                    })
                    print(f"   💾 Сохранено для визуализации")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

# Сохраняем статистику
if results:
    stats_file = results_dir / "glacier_correct_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Статистика сохранена: {stats_file}")

# ВИЗУАЛИЗАЦИИ
if glacier_images and len(glacier_images) >= 2:
    print("\n📊 Создание визуализаций...")
    
    # === ВИЗУАЛИЗАЦИЯ 1: Временная динамика ===
    n = len(glacier_images)
    fig = plt.figure(figsize=(6*n, 12))
    
    for idx, img in enumerate(glacier_images):
        # Верхний ряд: Оригинальные SAR данные
        ax1 = plt.subplot(3, n, idx + 1)
        im1 = ax1.imshow(img['data_db'], cmap='gray', vmin=15, vmax=30)
        ax1.set_title(f"{img['year']}\nSAR Backscatter (VV)", 
                     fontsize=14, fontweight='bold')
        ax1.axis('off')
        plt.colorbar(im1, ax=ax1, label='dB', fraction=0.046, pad=0.04)
        
        # Средний ряд: Цветная карта
        ax2 = plt.subplot(3, n, idx + 1 + n)
        im2 = ax2.imshow(img['data_db'], cmap='terrain', vmin=15, vmax=30)
        ax2.set_title(f"Цветная карта", fontsize=12, fontweight='bold')
        ax2.axis('off')
        plt.colorbar(im2, ax=ax2, label='dB', fraction=0.046, pad=0.04)
        
        # Нижний ряд: Сегментация (лед выделен)
        ax3 = plt.subplot(3, n, idx + 1 + 2*n)
        
        # Создаем RGB с выделением льда
        rgb = np.zeros((*img['data_db'].shape, 3))
        
        # Нормализуем backscatter для фона
        normalized = (img['data_db'] - 15) / 15
        normalized = np.clip(normalized, 0, 1)
        rgb[:,:,0] = normalized
        rgb[:,:,1] = normalized
        rgb[:,:,2] = normalized
        
        # Лед выделяем голубым
        rgb[img['ice_mask'], 0] = 0.1
        rgb[img['ice_mask'], 1] = 0.5
        rgb[img['ice_mask'], 2] = 1.0
        
        ax3.imshow(rgb)
        ax3.set_title(f"Площадь льда: {img['stats']['ice_area_km2']:.2f} км²\n"
                     f"Покрытие: {img['stats']['coverage_percent']:.1f}%",
                     fontsize=11, fontweight='bold')
        ax3.axis('off')
    
    plt.suptitle('Ледник Голубина: Реальные SAR снимки и анализ\n'
                 'Ala-Archa Gorge, Kyrgyzstan (Sentinel-1A, VV polarization)',
                fontsize=16, fontweight='bold', y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    output1 = viz_dir / "glacier_real_timeline.png"
    plt.savefig(output1, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Сохранено: {output1.name}")
    plt.close()
    
    # === ВИЗУАЛИЗАЦИЯ 2: Сравнение 2017 vs 2025 ===
    if len(glacier_images) >= 2:
        first = glacier_images[0]
        last = glacier_images[-1]
        
        fig = plt.figure(figsize=(20, 10))
        
        # === Панель 1: 2017 год ===
        # SAR данные
        ax1 = plt.subplot(2, 4, 1)
        im1 = ax1.imshow(first['data_db'], cmap='gray', vmin=15, vmax=30)
        ax1.set_title(f"{first['year']} - SAR Backscatter", fontsize=14, fontweight='bold')
        ax1.axis('off')
        plt.colorbar(im1, ax=ax1, label='dB', fraction=0.046)
        
        # Цветная карта
        ax2 = plt.subplot(2, 4, 2)
        im2 = ax2.imshow(first['data_db'], cmap='terrain', vmin=15, vmax=30)
        ax2.set_title(f"{first['year']} - Цветная карта", fontsize=14, fontweight='bold')
        ax2.axis('off')
        plt.colorbar(im2, ax=ax2, label='dB', fraction=0.046)
        
        # === Панель 2: 2025 год ===
        # SAR данные
        ax3 = plt.subplot(2, 4, 3)
        im3 = ax3.imshow(last['data_db'], cmap='gray', vmin=15, vmax=30)
        ax3.set_title(f"{last['year']} - SAR Backscatter", fontsize=14, fontweight='bold')
        ax3.axis('off')
        plt.colorbar(im3, ax=ax3, label='dB', fraction=0.046)
        
        # Цветная карта
        ax4 = plt.subplot(2, 4, 4)
        im4 = ax4.imshow(last['data_db'], cmap='terrain', vmin=15, vmax=30)
        ax4.set_title(f"{last['year']} - Цветная карта", fontsize=14, fontweight='bold')
        ax4.axis('off')
        plt.colorbar(im4, ax=ax4, label='dB', fraction=0.046)
        
        # === Нижний ряд ===
        # Сегментация 2017
        ax5 = plt.subplot(2, 4, 5)
        rgb1 = np.zeros((*first['data_db'].shape, 3))
        norm1 = (first['data_db'] - 15) / 15
        norm1 = np.clip(norm1, 0, 1)
        rgb1[:,:,:] = norm1[:,:,np.newaxis]
        rgb1[first['ice_mask'], :] = [0.1, 0.5, 1.0]
        ax5.imshow(rgb1)
        ax5.set_title(f"{first['year']} - Лед выделен\n"
                     f"Площадь: {first['stats']['ice_area_km2']:.2f} км²",
                     fontsize=12, fontweight='bold')
        ax5.axis('off')
        
        # Сегментация 2025
        ax6 = plt.subplot(2, 4, 6)
        rgb2 = np.zeros((*last['data_db'].shape, 3))
        norm2 = (last['data_db'] - 15) / 15
        norm2 = np.clip(norm2, 0, 1)
        rgb2[:,:,:] = norm2[:,:,np.newaxis]
        rgb2[last['ice_mask'], :] = [0.1, 0.5, 1.0]
        ax6.imshow(rgb2)
        ax6.set_title(f"{last['year']} - Лед выделен\n"
                     f"Площадь: {last['stats']['ice_area_km2']:.2f} км²",
                     fontsize=12, fontweight='bold')
        ax6.axis('off')
        
        # Разница backscatter
        ax7 = plt.subplot(2, 4, 7)
        diff_backscatter = last['data_db'] - first['data_db']
        im7 = ax7.imshow(diff_backscatter, cmap='RdBu_r', vmin=-5, vmax=5)
        ax7.set_title(f"Изменение Backscatter\n{first['year']} → {last['year']}",
                     fontsize=12, fontweight='bold')
        ax7.axis('off')
        plt.colorbar(im7, ax=ax7, label='Δ dB', fraction=0.046)
        
        # Карта изменений площади
        ax8 = plt.subplot(2, 4, 8)
        change_map = np.zeros(first['ice_mask'].shape)
        change_map[first['ice_mask'] & ~last['ice_mask']] = -1  # Потери
        change_map[~first['ice_mask'] & last['ice_mask']] = 1   # Прирост
        
        rgb_change = np.zeros((*first['data_db'].shape, 3))
        rgb_change[:,:,:] = norm1[:,:,np.newaxis]
        rgb_change[change_map == -1, :] = [1.0, 0.2, 0.2]  # Красный - потери
        rgb_change[change_map == 1, :] = [0.2, 1.0, 0.2]   # Зеленый - прирост
        rgb_change[(first['ice_mask'] & last['ice_mask']), :] = [0.1, 0.5, 1.0]  # Голубой - стабильно
        
        ax8.imshow(rgb_change)
        
        area_change = last['stats']['ice_area_km2'] - first['stats']['ice_area_km2']
        pct_change = (area_change / first['stats']['ice_area_km2']) * 100
        
        ax8.set_title(f"Изменение площади\n{area_change:+.2f} км² ({pct_change:+.1f}%)",
                     fontsize=12, fontweight='bold')
        ax8.axis('off')
        
        # Легенда
        red_patch = mpatches.Patch(color='red', label='Потери льда')
        green_patch = mpatches.Patch(color='green', label='Прирост льда')
        blue_patch = mpatches.Patch(color='cyan', label='Стабильная область')
        fig.legend(handles=[red_patch, green_patch, blue_patch],
                  loc='lower center', ncol=3, fontsize=14, frameon=True, fancybox=True)
        
        plt.suptitle(f'Детальное сравнение: {first["year"]} vs {last["year"]}\n'
                    f'Ледник Голубина, Ala-Archa Gorge',
                    fontsize=18, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        
        output2 = viz_dir / "glacier_detailed_comparison.png"
        plt.savefig(output2, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Сохранено: {output2.name}")
        plt.close()

# === ВИЗУАЛИЗАЦИЯ 3: График площади ===
if len(results) > 1:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    years = [r['year'] for r in results]
    areas = [r['ice_area_km2'] for r in results]
    backscatter = [r['mean_backscatter'] for r in results]
    
    # График 1: Площадь
    color1 = '#2E86AB'
    ax1.plot(years, areas, 'o-', linewidth=3, markersize=10, color=color1, label='Площадь льда')
    ax1.fill_between(years, areas, alpha=0.3, color=color1)
    ax1.set_xlabel('Год', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Площадь льда (км²)', fontsize=14, fontweight='bold', color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_title('Динамика площади ледника Голубина (2017-2025)', 
                 fontsize=16, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='upper left', fontsize=12)
    
    # Добавляем backscatter на второй оси
    ax1_twin = ax1.twinx()
    color2 = '#A23B72'
    ax1_twin.plot(years, backscatter, 's--', linewidth=2, markersize=8, 
                 color=color2, label='Средний backscatter', alpha=0.7)
    ax1_twin.set_ylabel('Backscatter (dB)', fontsize=14, fontweight='bold', color=color2)
    ax1_twin.tick_params(axis='y', labelcolor=color2)
    ax1_twin.legend(loc='upper right', fontsize=12)
    
    # Аннотации
    for year, area in zip(years, areas):
        ax1.annotate(f'{area:.1f}',
                    xy=(year, area),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
    
    # График 2: Изменения
    base_area = areas[0]
    changes = [(a - base_area) / base_area * 100 for a in areas]
    colors = ['green' if c >= 0 else 'red' for c in changes]
    
    bars = ax2.bar(years, changes, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_xlabel('Год', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Изменение (%)', fontsize=14, fontweight='bold')
    ax2.set_title(f'Изменение площади относительно {years[0]} года',
                 fontsize=16, fontweight='bold', pad=20)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=2)
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # Значения на столбцах
    for year, change, bar in zip(years, changes, bars):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{change:+.1f}%',
                ha='center',
                va='bottom' if change > 0 else 'top',
                fontsize=10,
                fontweight='bold')
    
    plt.tight_layout()
    output3 = viz_dir / "glacier_area_dynamics.png"
    plt.savefig(output3, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Сохранено: {output3.name}")
    plt.close()

# ФИНАЛЬНЫЙ ОТЧЕТ
print("\n" + "=" * 80)
print("📊 ИТОГОВАЯ СТАТИСТИКА")
print("=" * 80)

if results:
    first = results[0]
    last = results[-1]
    
    print(f"\n📈 Площадь льда:")
    print(f"   {first['year']}: {first['ice_area_km2']:.2f} км²")
    print(f"   {last['year']}: {last['ice_area_km2']:.2f} км²")
    
    area_change = last['ice_area_km2'] - first['ice_area_km2']
    pct_change = (area_change / first['ice_area_km2']) * 100
    
    print(f"\n📉 Изменение за {last['year'] - first['year']} лет:")
    print(f"   Абсолютное: {area_change:+.2f} км²")
    print(f"   Относительное: {pct_change:+.2f}%")
    
    print(f"\n📊 Backscatter:")
    print(f"   {first['year']}: {first['mean_backscatter']:.2f} dB")
    print(f"   {last['year']}: {last['mean_backscatter']:.2f} dB")
    print(f"   Изменение: {last['mean_backscatter'] - first['mean_backscatter']:+.2f} dB")
    
    if abs(pct_change) < 1.0:
        print(f"\n✅ ВЫВОД: Площадь ледника относительно стабильна")
    elif pct_change < -1.0:
        print(f"\n⚠️  ВЫВОД: Ледник сокращается ({pct_change:.1f}%)")
    else:
        print(f"\n📈 ВЫВОД: Ледник растет ({pct_change:.1f}%)")
    
    print(f"\n📁 Результаты:")
    print(f"   • glacier_real_timeline.png - реальные SAR снимки")
    print(f"   • glacier_detailed_comparison.png - детальное сравнение")
    print(f"   • glacier_area_dynamics.png - динамика площади")
    print(f"   • glacier_correct_statistics.json - статистика")

print("\n" + "=" * 80)
print("✅ АНАЛИЗ С РЕАЛЬНЫМИ ДАННЫМИ ЗАВЕРШЕН!")
print("=" * 80)
print()


