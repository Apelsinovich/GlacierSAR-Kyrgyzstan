#!/usr/bin/env python3
"""
Скачивание SAR изображений с использованием Bearer токена
"""

import asf_search as asf
from datetime import datetime
import yaml
from pathlib import Path
import sys
import os


def download_with_bearer_token(bearer_token, start_year=2017, end_year=2025, max_downloads=9):
    """Скачивание с использованием Bearer токена"""
    
    print("=" * 80)
    print("🏔️  СКАЧИВАНИЕ ИЗОБРАЖЕНИЙ ЛЕДНИКА ГОЛУБИНА С ТОКЕНОМ")
    print("=" * 80)
    
    # Загружаем конфигурацию
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Получаем координаты ледника
    bbox_config = config['sar_data']['api_download']['target_glacier_bbox']
    
    # Параметры поиска
    wkt_aoi = f"POLYGON(({bbox_config['min_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['min_lat']}))"
    
    print(f"📍 Область: Ледник Голубина, Ала-Арча")
    print(f"   Координаты: {bbox_config['min_lon']}, {bbox_config['min_lat']} - "
          f"{bbox_config['max_lon']}, {bbox_config['max_lat']}")
    
    # Директория для сохранения
    output_dir = Path("output/raw_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Директория: {output_dir}")
    
    target_month = config['sar_data']['api_download']['target_month']
    
    print(f"\n⏰ Период: {start_year} - {end_year}")
    print(f"📅 Месяц: {target_month} (июль - пик таяния)")
    print(f"🛰️  Спутник: Sentinel-1A")
    print(f"📡 Поляризация: VV+VH")
    print(f"🎯 Максимум: {max_downloads} снимков")
    
    all_results = []
    
    # Поиск по годам
    print("\n🔍 Поиск доступных снимков...")
    for year in range(start_year, end_year + 1):
        if len(all_results) >= max_downloads:
            print(f"✋ Достигнут лимит ({max_downloads}), остановка поиска")
            break
            
        start_date = f"{year}-{target_month-1:02d}-01" if target_month > 1 else f"{year}-01-01"
        end_date = f"{year}-{target_month+1:02d}-30" if target_month < 12 else f"{year}-12-31"
        
        try:
            results = asf.geo_search(
                platform=[asf.PLATFORM.SENTINEL1],
                intersectsWith=wkt_aoi,
                start=start_date,
                end=end_date,
                processingLevel=[asf.PRODUCT_TYPE.GRD_HD],
                beamMode=[asf.BEAMMODE.IW],
            )
            
            if results:
                target_date = datetime(year, target_month, 15)
                best_result = None
                min_diff = float('inf')
                
                for r in results:
                    scene_date_str = r.properties['startTime']
                    if isinstance(scene_date_str, str):
                        scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
                    else:
                        scene_date = scene_date_str
                    
                    diff = abs((scene_date.replace(tzinfo=None) - target_date).days)
                    if diff < min_diff:
                        min_diff = diff
                        best_result = r
                
                if best_result:
                    all_results.append(best_result)
                    scene_date_str = best_result.properties['startTime']
                    if isinstance(scene_date_str, str):
                        scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
                    else:
                        scene_date = scene_date_str
                    scene_date_formatted = scene_date.strftime('%Y-%m-%d')
                    file_size = best_result.properties.get('bytes', 0) / (1024**3)
                    print(f"✅ {year}: найден снимок от {scene_date_formatted} (~{file_size:.2f} GB)")
            else:
                print(f"❌ {year}: снимков не найдено")
                
        except Exception as e:
            print(f"❌ {year}: ошибка поиска - {e}")
    
    if not all_results:
        print("\n❌ Не найдено доступных снимков!")
        return []
    
    print(f"\n📊 Всего найдено: {len(all_results)} снимков")
    
    # Показываем детали
    print("\n📋 Детали найденных снимков:")
    print("-" * 80)
    for i, result in enumerate(all_results, 1):
        props = result.properties
        scene_date_str = props['startTime']
        if isinstance(scene_date_str, str):
            scene_date = datetime.fromisoformat(scene_date_str.replace('Z', '+00:00'))
        else:
            scene_date = scene_date_str
        print(f"{i}. Дата: {scene_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Спутник: {props['platform']}")
        print(f"   Размер: {props.get('bytes', 0)/(1024**3):.2f} GB")
        print(f"   Файл: {props['fileName']}")
        print()
    
    total_size = sum(r.properties.get('bytes', 0) for r in all_results) / (1024**3)
    print(f"💾 Общий размер: {total_size:.2f} GB")
    print(f"⏱️  Примерное время: {total_size*2:.0f}-{total_size*5:.0f} минут")
    
    print("\n📥 Начинаем скачивание с Bearer токеном...")
    
    # Создаем сессию с Bearer токеном
    session = asf.ASFSession()
    session.auth_with_token(bearer_token)
    
    downloaded_count = 0
    failed_files = []
    
    try:
        for i, result in enumerate(all_results, 1):
            filename = result.properties['fileName']
            output_path = output_dir / filename
            
            print(f"\n[{i}/{len(all_results)}] Скачивание: {filename}")
            
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024**2)
                print(f"   ⏭️  Файл уже существует ({file_size_mb:.1f} MB), пропускаем")
                downloaded_count += 1
                continue
            
            try:
                print(f"   ⬇️  Начало скачивания...")
                result.download(path=str(output_dir), session=session)
                
                if output_path.exists():
                    file_size_mb = output_path.stat().st_size / (1024**2)
                    print(f"   ✅ Скачано успешно ({file_size_mb:.1f} MB)")
                    downloaded_count += 1
                else:
                    print(f"   ⚠️  Файл не найден после скачивания")
                    failed_files.append(filename)
                    
            except Exception as e:
                print(f"   ❌ Ошибка скачивания: {e}")
                failed_files.append(filename)
        
        print("\n" + "=" * 80)
        print("✅ СКАЧИВАНИЕ ЗАВЕРШЕНО")
        print("=" * 80)
        print(f"📊 Успешно: {downloaded_count}/{len(all_results)} файлов")
        
        if failed_files:
            print(f"\n⚠️  Не удалось скачать {len(failed_files)} файлов:")
            for fname in failed_files:
                print(f"   • {fname}")
        
        print(f"\n📁 Файлы сохранены в: {output_dir}")
        print("🚀 Готово к обработке!")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    return all_results


if __name__ == "__main__":
    # Получаем токен из аргумента командной строки или переменной окружения
    bearer_token = None
    
    if len(sys.argv) > 1:
        bearer_token = sys.argv[1]
    elif 'EARTHDATA_TOKEN' in os.environ:
        bearer_token = os.environ['EARTHDATA_TOKEN']
    else:
        print("❌ Ошибка: Bearer токен не предоставлен!")
        print("\nИспользование:")
        print("  Вариант 1: python3 download_with_token.py YOUR_TOKEN")
        print("  Вариант 2: export EARTHDATA_TOKEN='YOUR_TOKEN' && python3 download_with_token.py")
        sys.exit(1)
    
    print("🔐 Bearer токен получен")
    
    try:
        results = download_with_bearer_token(
            bearer_token=bearer_token,
            start_year=2017,
            end_year=2025,
            max_downloads=9
        )
        
        if results:
            print(f"\n✅ Операция завершена! Найдено и обработано {len(results)} снимков.")
        else:
            print("\n⚠️  Снимков не найдено.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


