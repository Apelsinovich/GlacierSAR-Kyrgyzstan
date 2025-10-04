#!/usr/bin/env python3
"""
Автоматическое скачивание изображений ледника Голубина через ASF API
С поддержкой параметров командной строки
"""

import asf_search as asf
from datetime import datetime
import yaml
from pathlib import Path
import argparse


def download_glacier_images(auto_download=False, start_year=2015, end_year=2025, max_downloads=10):
    """Скачивание SAR изображений ледника Голубина"""
    
    print("=" * 80)
    print("🏔️  СКАЧИВАНИЕ ИЗОБРАЖЕНИЙ ЛЕДНИКА ГОЛУБИНА")
    print("=" * 80)
    
    # Загружаем конфигурацию
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Получаем координаты ледника из конфига
    bbox_config = config['sar_data']['api_download']['target_glacier_bbox']
    
    # Параметры поиска
    wkt_aoi = f"POLYGON(({bbox_config['min_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['min_lat']}, " \
              f"{bbox_config['max_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['max_lat']}, " \
              f"{bbox_config['min_lon']} {bbox_config['min_lat']}))"
    
    print(f"📍 Область интереса: Ледник Голубина, Ала-Арча")
    print(f"   Координаты: {bbox_config['min_lon']}, {bbox_config['min_lat']} - "
          f"{bbox_config['max_lon']}, {bbox_config['max_lat']}")
    
    # Директория для сохранения
    output_dir = Path("output/raw_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Директория для сохранения: {output_dir}")
    
    # Параметры поиска
    target_month = config['sar_data']['api_download']['target_month']
    
    print(f"\n⏰ Временной период: {start_year} - {end_year}")
    print(f"📅 Целевой месяц: {target_month} (июль - пик таяния)")
    print(f"🛰️  Спутник: Sentinel-1")
    print(f"📡 Поляризация: VV+VH (dual-pol)")
    print(f"🎯 Максимум снимков: {max_downloads}")
    
    all_results = []
    
    # Поиск по годам
    print("\n🔍 Поиск доступных снимков...")
    for year in range(start_year, end_year + 1):
        if len(all_results) >= max_downloads:
            print(f"✋ Достигнут лимит снимков ({max_downloads}), остановка поиска")
            break
            
        # Расширенный период поиска (месяц ±1)
        start_date = f"{year}-{target_month-1:02d}-01" if target_month > 1 else f"{year}-01-01"
        end_date = f"{year}-{target_month+1:02d}-30" if target_month < 12 else f"{year}-12-31"
        
        try:
            # Поиск через ASF
            results = asf.geo_search(
                platform=[asf.PLATFORM.SENTINEL1],
                intersectsWith=wkt_aoi,
                start=start_date,
                end=end_date,
                processingLevel=[asf.PRODUCT_TYPE.GRD_HD],
                beamMode=[asf.BEAMMODE.IW],
            )
            
            if results:
                # Фильтруем по месяцу и выбираем лучший снимок
                target_date = datetime(year, target_month, 15)
                best_result = None
                min_diff = float('inf')
                
                for r in results:
                    scene_date_str = r.properties['startTime']
                    # Преобразуем строку в datetime
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
                    file_size = best_result.properties.get('bytes', 0) / (1024**3)  # GB
                    print(f"✅ {year}: найден снимок от {scene_date_formatted} "
                          f"(~{file_size:.2f} GB)")
            else:
                print(f"❌ {year}: снимков не найдено")
                
        except Exception as e:
            print(f"❌ {year}: ошибка поиска - {e}")
    
    if not all_results:
        print("\n❌ Не найдено доступных снимков!")
        print("💡 Попробуйте расширить временной диапазон или изменить область поиска")
        return []
    
    print(f"\n📊 Всего найдено снимков: {len(all_results)}")
    
    # Показываем детали найденных снимков
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
        print(f"   Режим: {props['beamModeType']}")
        print(f"   Поляризация: {props.get('polarization', 'N/A')}")
        print(f"   Размер: {props.get('bytes', 0)/(1024**3):.2f} GB")
        print(f"   Имя файла: {props['fileName']}")
        print()
    
    # Спрашиваем про скачивание
    total_size = sum(r.properties.get('bytes', 0) for r in all_results) / (1024**3)
    print(f"💾 Общий размер для скачивания: {total_size:.2f} GB")
    print(f"⏱️  Примерное время скачивания: {total_size*2:.0f}-{total_size*5:.0f} минут")
    
    if not auto_download:
        print("\n💡 Для автоматического скачивания используйте: --download")
        print("💡 Для скачивания нужны учетные данные NASA Earthdata")
        print("💡 Регистрация: https://urs.earthdata.nasa.gov/users/new")
        print("\n📝 Список файлов для ручного скачивания через https://search.asf.alaska.edu:")
        for result in all_results:
            print(f"   • {result.properties['fileName']}")
        return all_results
    
    print("\n📥 Начинаем автоматическое скачивание...")
    print("⚠️  ВАЖНО: Для скачивания нужны учетные данные NASA Earthdata")
    print("   Регистрация: https://urs.earthdata.nasa.gov/users/new")
    print()
    
    # Попытка скачивания
    session = asf.ASFSession()
    
    downloaded_count = 0
    try:
        # Скачиваем каждый файл
        for i, result in enumerate(all_results, 1):
            filename = result.properties['fileName']
            output_path = output_dir / filename
            
            print(f"\n[{i}/{len(all_results)}] Скачивание: {filename}")
            
            if output_path.exists():
                print(f"   ⏭️  Файл уже существует, пропускаем")
                downloaded_count += 1
                continue
            
            try:
                result.download(path=str(output_dir), session=session)
                print(f"   ✅ Скачано успешно")
                downloaded_count += 1
            except Exception as e:
                print(f"   ❌ Ошибка скачивания: {e}")
        
        print("\n" + "=" * 80)
        print("✅ СКАЧИВАНИЕ ЗАВЕРШЕНО")
        print("=" * 80)
        print(f"📊 Скачано: {downloaded_count}/{len(all_results)} файлов")
        print(f"📁 Файлы сохранены в: {output_dir}")
        print("🚀 Готово к обработке в pipeline!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при скачивании: {e}")
        print("\n💡 Возможные решения:")
        print("   1. Зарегистрируйтесь на https://urs.earthdata.nasa.gov")
        print("   2. Используйте ручное скачивание через https://search.asf.alaska.edu")
        print("   3. Настройте credentials в .netrc файле")
    
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Скачивание SAR изображений ледника Голубина через ASF API'
    )
    parser.add_argument('--download', action='store_true',
                       help='Начать автоматическое скачивание (требуется NASA Earthdata аккаунт)')
    parser.add_argument('--start-year', type=int, default=2015,
                       help='Начальный год (по умолчанию: 2015)')
    parser.add_argument('--end-year', type=int, default=2025,
                       help='Конечный год (по умолчанию: 2025)')
    parser.add_argument('--max', type=int, default=10,
                       help='Максимальное количество снимков (по умолчанию: 10)')
    
    args = parser.parse_args()
    
    try:
        results = download_glacier_images(
            auto_download=args.download,
            start_year=args.start_year,
            end_year=args.end_year,
            max_downloads=args.max
        )
        
        if results:
            print(f"\n✅ Операция завершена успешно! Найдено {len(results)} снимков.")
        else:
            print("\n⚠️  Снимков не найдено или возникла ошибка.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


