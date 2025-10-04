# 🚀 Быстрый старт: Чек-лист (10 минут)

## ✅ ШАГ 1: Установка (2 минуты)
```bash
# Проверка Python версии
python3 --version  # Должно быть 3.8+

# Установка основных библиотек
pip3 install numpy matplotlib scipy rasterio geopandas pyyaml

# Проверка работоспособности
python3 sar_pipeline.py  # Должно вывести приветствие
```

## ✅ ШАГ 2: Данные (3 минуты)
```bash
# 1. Перейдите на https://search.asf.alaska.edu/
# 2. Введите координаты: 42.565, 74.5 (Ala-Archa)
# 3. Фильтры:
#    - Dataset: Sentinel-1
#    - Polarization: VV+VH (или VV)
#    - Product: GRD_HD
#    - Даты: июнь 2023 + июнь 2024
# 4. Скачайте 2 файла
# 5. Поместите в output/raw_data/
```

## ✅ ШАГ 3: Тестовый запуск (2 минуты)
```bash
# Запуск примеров с синтетическими данными
python3 example_workflow.py

# Результаты появятся в output/visualizations/
```

## ✅ ШАГ 3.1: Автоматизированное скачивание (5 минут)
```bash
# Скачайте данные за 10 лет для ледника Голубина
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Или запустите полный пайплайн автоматически
python3 run_full_pipeline.py
```

## ✅ ШАГ 5: Реальный анализ (3 минуты)
```python
from sar_pipeline import SARGlacierPipeline

# Инициализация
pipeline = SARGlacierPipeline('config.yaml')

# Загрузка ваших данных
img1 = pipeline.preprocess_sar_image('output/raw_data/ваш_файл_2023.tif')
img2 = pipeline.preprocess_sar_image('output/raw_data/ваш_файл_2024.tif')

# Анализ изменений
results = pipeline.compare_images(img1, img2, '2023-06-01', '2024-06-01')

# Визуализация
pipeline.visualize_comparison(img1, img2, results, 'output/comparison.png')

print("Готово! Проверьте output/visualizations/")
```

---

## 🎯 ГЛАВНОЕ: VV ПОЛЯРИЗАЦИЯ
**Используйте VV (Vertical-Vertical)** поляризацию Sentinel-1 для оптимального обнаружения таяния ледников!

**Почему VV?**
- ✅ Максимальная чувствительность к талой воде
- ✅ Высокий контраст между сухим и влажным льдом
- ✅ Доступна в 100% снимков Sentinel-1

---

## 📁 Структура проекта
```
GlacierSAR-Kyrgyzstan/
├── sar_pipeline.py          # Основной код
├── config.yaml             # Конфигурация
├── example_workflow.py     # Примеры
├── requirements.txt        # Зависимости
├── QUICK_START.md          # Подробный гид
└── output/                 # Результаты
```

---

## 🔧 Если проблемы

### Ошибка импорта:
```bash
pip3 install rasterio geopandas scikit-image
```

### Нет данных:
```bash
# Автоматически скачайте данные за 10 лет:
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Или скачайте вручную с ASF (см. QUICK_START.md)
# Или используйте синтетические данные из example_workflow.py
```

### Вопросы:
- См. `QUICK_START.md` для подробностей
- См. `DEBRIS_CLASSIFICATION.md` для улучшенной классификации

---

## 🎉 ГОТОВО!
Теперь у вас есть рабочий пайплайн для мониторинга ледников Ala-Archa с использованием SAR данных!

**Следующие шаги:**
1. Автоматически скачайте данные за 10 лет: `python3 asf_api_downloader.py --years 2015 2025 --month 7`
2. Обработайте временные ряды: `python3 time_series_processor.py`
3. Или запустите полный пайплайн: `python3 run_full_pipeline.py`
4. Создайте презентацию с результатами
5. Profit! 🚀

---

**Команда TengriSpacers** | **NASA Space Apps Challenge 2025**


