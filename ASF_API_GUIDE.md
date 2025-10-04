# ASF API Guide: Автоматизированное скачивание Sentinel-1 данных

## 🚀 Быстрое начало

```bash
# 1. Установите зависимости
pip3 install requests

# 2. Скачайте данные за 10 лет для ледника Голубина
python3 asf_api_downloader.py --years 2015 2025 --month 7

# 3. Или запустите полный пайплайн автоматически
python3 run_full_pipeline.py
```

---

## 📋 Параметры ASF API

### Основные параметры поиска:

| Параметр | Описание | Пример значения |
|----------|----------|-----------------|
| `platform` | Спутниковая платформа | `"Sentinel-1"` |
| `processingLevel` | Уровень обработки | `"GRD_HD"` |
| `beamMode` | Режим съёмки | `"IW"` |
| `polarization` | Поляризация | `"VV+VH"` |
| `start` | Дата начала | `"2015-07-01"` |
| `end` | Дата окончания | `"2025-07-31"` |
| `bbox` | Границы области | `"74.5,42.56,74.52,42.58"` |

### Конфигурация для ледника Голубина:

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
  target_month: 7  # Июль - пик таяния
  polarization: "VV+VH"
  max_downloads: 15
```

---

## 🗓️ Стратегия сканирования

### Ежегодные летние снимки:

```python
# Скачиваем по одному снимку за июль каждого года
for year in range(2015, 2026):
    start_date = f"{year}-06-15"
    end_date = f"{year}-08-15"

    # Ищем лучший снимок в этом периоде
    granules = search_granules(bbox, start_date, end_date)
    best_granule = select_best_annual_scene(granules, target_month=7)
    download_granule(best_granule)
```

### Преимущества подхода:
- ✅ Один снимок в год в пик сезона таяния
- ✅ Минимальный объём данных (10-15 файлов)
- ✅ Достаточно для анализа трендов за 10 лет
- ✅ Фокус на летний период (максимальное таяние)

---

## 🔧 Примеры использования

### Пример 1: Скачивание для конкретного ледника

```python
from asf_api_downloader import ASFAPIDownloader

# Инициализация
downloader = ASFAPIDownloader()

# Координаты ледника Голубина
bbox = (74.5000, 42.5600, 74.5200, 42.5800)

# Скачивание за 10 лет
downloaded_files = downloader.download_time_series(
    bbox=bbox,
    start_year=2015,
    end_year=2025,
    target_month=7,  # Июль
    polarization="VV+VH"
)
```

### Пример 2: Кастомные параметры

```python
# Скачивание для другого региона/периода
custom_files = downloader.download_time_series(
    bbox=(74.45, 42.55, 74.55, 42.65),  # Другой регион
    start_year=2020,
    end_year=2023,
    target_month=8,  # Август
    polarization="VV",
    max_downloads=5
)
```

### Пример 3: Тестовое скачивание

```python
# Маленький тест для проверки работоспособности
test_files = downloader.download_time_series(
    bbox=(74.50, 42.56, 74.52, 42.58),  # Очень маленькая область
    start_year=2022,
    end_year=2023,
    target_month=7,
    polarization="VV",
    max_downloads=2  # Только 2 файла
)
```

---

## 📊 Структура ответа ASF API

### Пример ответа поиска:

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

### Ключевые поля:
- `sceneDate`: Дата съёмки
- `downloadUrl`: Прямая ссылка для скачивания
- `polarization`: Доступные поляризации
- `sizeMB`: Размер файла в МБ

---

## 🚨 Важные замечания

### Ограничения ASF API:
- **Бесплатно** для научных целей
- **Лимит запросов**: ~1000 в час (для предотвращения злоупотреблений)
- **Размер файлов**: Sentinel-1 GRD ~800-900 МБ каждый
- **Время скачивания**: 1-2 минуты на файл (зависит от скорости интернета)

### Обработка ошибок:

```python
try:
    granules = downloader.search_granules(bbox, start_date, end_date)
    if not granules:
        print("❌ Нет данных для указанного периода")
        return

    downloaded = downloader.download_time_series(...)
    print(f"✅ Скачано {len(downloaded)} файлов")

except requests.exceptions.RequestException as e:
    print(f"❌ Ошибка сети: {e}")
except Exception as e:
    print(f"❌ Другая ошибка: {e}")
```

### Рекомендации:
1. **Начинайте с тестового скачивания** маленькой области
2. **Используйте VPN** если есть проблемы с доступом
3. **Проверяйте лимиты ASF** для интенсивного использования

---

## 🎯 Для вашего проекта

### Ледник Голубина (Ala-Archa):

```bash
# Рекомендуемая команда для вашего проекта:
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Это скачает:
# • 2015-07: S1A_IW_GRDH_1SDV_201507xx_VV_VH.zip
# • 2016-07: S1A_IW_GRDH_1SDV_201607xx_VV_VH.zip
# • ... (по одному файлу за каждый год)
# • 2025-07: S1A_IW_GRDH_1SDV_202507xx_VV_VH.zip
```

### Ожидаемые результаты:
- 📁 **11 файлов** (2015-2025)
- 📊 **~10 ГБ** данных
- ⏱️ **15-20 минут** на скачивание
- 🎯 **Готовые данные** для анализа временных рядов

---

## 🔗 Полезные ссылки

- **ASF API документация**: https://docs.asf.alaska.edu/api/
- **ASF поисковый интерфейс**: https://search.asf.alaska.edu/
- **Sentinel-1 информация**: https://sentinel.esa.int/web/sentinel/missions/sentinel-1

---

## ✅ Итоговые рекомендации

1. **Используйте ASF API** для автоматизации
2. **Начинайте с тестового скачивания** маленькой области
3. **Скачивайте VV+VH поляризацию** для лучшей классификации
4. **Выбирайте июль** для анализа пика таяния
5. **Ограничивайте количество** файлов разумными пределами

**Результат**: Полностью автоматизированный сбор данных за 10 лет для анализа таяния ледника Голубина! 🚀

---

**Команда TengriSpacers** | **NASA Space Apps Challenge 2025**

