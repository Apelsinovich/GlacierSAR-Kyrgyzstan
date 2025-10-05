# Quick Start Guide
## SAR Glacier Monitoring Pipeline - Ala-Archa Glaciers

Быстрый старт для команды TengriSpacers на NASA Space Apps Challenge 2025

---

## 🚀 Установка (5 минут)

### 1. Установите зависимости

```bash
# Убедитесь, что у вас Python 3.8+
python --version

# Установите основные библиотеки
pip install numpy scipy pandas matplotlib seaborn
pip install rasterio geopandas shapely
pip install scikit-image scikit-learn
pip install pyyaml tqdm

# Опционально (для полной функциональности):
pip install -r requirements.txt
```

### 2. Проверьте установку

```bash
python sar_pipeline.py
```

Должно вывести приветственное сообщение и рекомендацию по поляризации.

---

## 📥 Получение SAR данных (10 минут)

### Рекомендуемый источник: Alaska Satellite Facility (ASF)

1. **Перейдите**: https://search.asf.alaska.edu/

2. **Найдите область**:
   - Введите координаты: `42.565, 74.5`
   - Или нарисуйте область вокруг Ala-Archa на карте

3. **Настройте фильтры**:
   ```
   Dataset: Sentinel-1
   Beam Mode: IW
   Polarization: VV+VH (или только VV)
   Product Type: GRD_HD
   Date From: 2020-01-01
   Date To: 2025-10-04
   ```

4. **Выберите изображения**:
   - Минимум: 2 изображения (разные годы, один сезон)
   - Рекомендуется: 4-6 изображений (июнь каждого года)
   - Оптимально: 12+ изображений (ежемесячно)

5. **Скачайте**:
   - Формат: GeoTIFF (если доступен)
   - Или ZIP архивы Sentinel-1 GRD

6. **Разместите данные**:
   ```bash
   mkdir -p output/raw_data
   # Переместите скачанные файлы в output/raw_data/
   ```

---

## 🎯 Быстрый анализ (15 минут)

### Вариант 1: Запуск примеров с синтетическими данными

```bash
python example_workflow.py
```

Это создаст:
- ✓ `output/visualizations/example_comparison.png` - Сравнение двух изображений
- ✓ `output/visualizations/timeseries_example.png` - График временных рядов
- ✓ `output/reports/glacier_analysis_report.md` - Полный отчёт

### Вариант 2: Автоматизированное скачивание данных

Для ледника Голубина в Ала-Арча:

```bash
# Скачайте данные за 10 лет (июль каждого года) - ~5 минут
python3 asf_api_downloader.py --years 2015 2025 --month 7

# Или используйте полный пайплайн
python3 run_full_pipeline.py
```

Это автоматически:
- Скачает по одному снимку Sentinel-1 VV+VH за июль каждого года
- Обработает все данные через пайплайн
- Создаст анализ временных рядов
- Сгенерирует визуализации и отчёты

### Вариант 3: Анализ реальных данных

Создайте файл `my_analysis.py`:

```python
from sar_pipeline import SARGlacierPipeline

# Инициализация
pipeline = SARGlacierPipeline('config.yaml')

# ЗАМЕНИТЕ на ваши пути к файлам!
img1 = pipeline.preprocess_sar_image(
    'output/raw_data/your_image_2023.tif',
    'output/preprocessed/img_2023.tif'
)

img2 = pipeline.preprocess_sar_image(
    'output/raw_data/your_image_2024.tif',
    'output/preprocessed/img_2024.tif'
)

# Сравнение
results = pipeline.compare_images(img1, img2, '2023-06-15', '2024-06-15')

# Визуализация
pipeline.visualize_comparison(
    img1, img2, results,
    'output/visualizations/my_comparison.png'
)

print("Готово! Проверьте output/visualizations/")
```

Запустите:
```bash
python my_analysis.py
```

---

## 📊 Что вы получите

### 1. Визуализация сравнения
- 6 панелей с анализом изменений
- Цветные карты изменений
- Статистика

### 2. Временной ряд
- График площади ледников
- Тренд изменений
- Скорость таяния

### 3. Отчёт
- Методология
- Результаты
- Интерпретация
- Рекомендации

---

## 🎓 Для презентации

### Ключевые моменты:

1. **Выбор поляризации: VV** ⭐
   - Почему: наиболее чувствительна к талой воде
   - Альтернативы: HH, полная поляриметрия
   - Источник: `POLARIZATION_GUIDE.md`

2. **Методология**:
   - Preprocessing: калибровка + фильтрация спекла
   - Detection: пороговый метод
   - Change detection: разность изображений
   - Time series: линейная регрессия

3. **Результаты**:
   - Показывайте карты изменений (синие = таяние)
   - Количественные метрики (км²/год)
   - Временные тренды

4. **Воздействие**:
   - Водные ресурсы Бишкека
   - Риск наводнений
   - Долгосрочные прогнозы

---

## 📚 Структура проекта

```
GlacierSAR-Kyrgyzstan/
├── config.yaml                 # Конфигурация
├── sar_pipeline.py             # Основной пайплайн
├── example_workflow.py         # Примеры использования
├── requirements.txt            # Зависимости Python
├── POLARIZATION_GUIDE.md       # Подробный гид по поляризации
├── QUICK_START.md              # Этот файл
├── README.md                   # Описание проекта
└── output/                     # Результаты
    ├── raw_data/              # Исходные SAR данные
    ├── preprocessed/          # Обработанные изображения
    ├── visualizations/        # Графики и карты
    └── reports/               # Отчёты в Markdown
```

---

## 🔧 Настройка

### Редактирование config.yaml

```yaml
# Измените область исследования
study_area:
  center_lat: 42.5650  # Ваша широта
  center_lon: 74.5000  # Ваша долгота

# Измените поляризацию (если используете другую)
sar_data:
  polarization: "VV"  # или "HH", "HV", "VH"

# Измените параметры обработки
processing:
  preprocessing:
    speckle_filter: "Lee"  # или "Frost", "Refined Lee"
    filter_size: 5
```

---

## ❓ Troubleshooting

### Проблема: "ModuleNotFoundError: No module named 'rasterio'"
**Решение**:
```bash
pip install rasterio
# Если не работает:
conda install -c conda-forge rasterio
```

### Проблема: "Cannot open GeoTIFF file"
**Решение**:
- Проверьте путь к файлу
- Убедитесь, что файл в формате GeoTIFF (.tif)
- Попробуйте открыть в QGIS для проверки

### Проблема: Изображения разного размера
**Решение**:
- Все изображения должны быть из одного региона
- Используйте одинаковый режим съёмки (IW)
- При необходимости обрежьте до общей области

### Проблема: "GDAL not found"
**Решение**:
```bash
# Windows
conda install -c conda-forge gdal

# Mac
brew install gdal
pip install gdal

# Linux
sudo apt-get install gdal-bin libgdal-dev
pip install gdal
```

---

## 🎯 Минимальный путь к результату (30 минут)

Если времени мало, следуйте этому плану:

1. **[5 мин]** Установите базовые библиотеки:
   ```bash
   pip install numpy matplotlib rasterio geopandas pyyaml
   ```

2. **[5 мин]** Запустите пример с синтетическими данными:
   ```bash
   python example_workflow.py
   ```

3. **[10 мин]** Скачайте 2 реальных Sentinel-1 изображения с ASF

4. **[10 мин]** Адаптируйте пример под ваши данные

5. **[Готово!]** Используйте результаты в презентации

---

## 📞 Контакты команды

- **Dmitrii Pecherkin** — Team Lead
- **Mikhail Vasilyev** — Developer
- **Farit Gatiatullin** — Developer
- **Kenenbek Arzymatov** — Data Scientist
- **Juozas Bechelis** — Contributor

**Team**: TengriSpacers  
**Challenge**: https://www.spaceappschallenge.org/2025/challenges/through-the-radar-looking-glass-revealing-earth-processes-with-sar/

---

## ✨ Дополнительные ресурсы

- **NASA SAR Tutorial**: https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar
- **Sentinel-1 Toolbox**: https://step.esa.int/main/toolboxes/snap/
- **QGIS для визуализации**: https://qgis.org
- **Google Earth Engine** (для продвинутых): https://earthengine.google.com

---

**Удачи на конкурсе! 🚀🌍❄️**


