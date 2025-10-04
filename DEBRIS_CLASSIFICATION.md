# Решение проблемы различения камней и льда в SAR данных
## Методы классификации обломочного покрова на ледниках

---

## 🎯 Проблема

В SAR данных уровни обратного рассеяния у камней (обломочного покрова) и льда часто бывают очень похожими, что затрудняет:

- ✅ Различение ледниковой поверхности от окружающих скал
- ✅ Определение границ ледников под обломочным покровом
- ✅ Мониторинг динамики ледников с обломочным покровом
- ✅ Оценку реальной площади ледников

---

## 🔬 Физические основы различий

### Характеристики обратного рассеяния:

| Тип поверхности | VV поляризация (σ⁰, dB) | HV/VH поляризация (σ⁰, dB) | Различия |
|----------------|-------------------------|---------------------------|----------|
| **Чистый лёд** | -8 до -3 | -15 до -10 | Высокий VV, низкий кросс-пол |
| **Влажный лёд** | -18 до -12 | -20 до -15 | Низкий VV, очень низкий кросс-пол |
| **Сухие скалы** | -10 до -5 | -12 до -8 | Высокий VV, средний кросс-пол |
| **Обломочный покров** | -12 до -6 | -14 до -9 | Переменный, зависит от влажности |
| **Влажные камни** | -15 до -10 | -18 до -12 | Низкий VV, низкий кросс-пол |

---

## 🛠️ Методы решения

### 1. Много-поляризационный подход

#### Использование кросс-поляризации (HV/VH):
- **Преимущество**: HV/VH менее чувствительна к геометрии поверхности
- **Метод**: Отношение VV/HV > 5-7 dB указывает на чистый лёд
- **Реализация**: Используйте dual-pol (VV+VH) продукты Sentinel-1

#### Код для классификации:
```python
def classify_ice_vs_debris(vv_image, vh_image):
    """
    Классификация льда vs обломочного покрова
    """
    # Отношение поляризаций
    ratio = vv_image / (vh_image + 1e-10)
    ratio_db = 10 * np.log10(ratio + 1e-10)

    # Порог для различения
    ice_threshold = 7  # dB (настраиваемый)

    # Классификация
    ice_mask = ratio_db > ice_threshold
    debris_mask = ratio_db <= ice_threshold

    return ice_mask, debris_mask, ratio_db
```

### 2. Временной анализ

#### Много-временные изменения:
- **Лёд**: Показывает сильные сезонные изменения (таяние летом)
- **Камни**: Стабильное обратное рассеяние во времени
- **Метод**: Анализ дисперсии временных рядов

#### Код для временного анализа:
```python
def temporal_classification(time_series):
    """
    Классификация по временным изменениям
    """
    # Стандартное отклонение временных рядов
    std_dev = np.std(time_series, axis=0)

    # Порог стабильности (камни имеют низкую дисперсию)
    stability_threshold = 2  # dB

    # Стабильные области = камни/обломки
    stable_mask = std_dev < stability_threshold

    # Переменные области = лёд/снег
    variable_mask = std_dev >= stability_threshold

    return stable_mask, variable_mask, std_dev
```

### 3. Текстурный анализ

#### Текстурные характеристики:
- **Лёд**: Более гладкая поверхность, низкая текстурная изменчивость
- **Обломки**: Шероховатая поверхность, высокая локальная изменчивость

#### Методы текстурного анализа:
```python
def texture_analysis(sar_image, window_size=5):
    """
    Анализ текстуры для классификации
    """
    from skimage.feature import graycomatrix, graycoprops

    # Нормализация изображения
    normalized = (sar_image - sar_image.min()) / (sar_image.max() - sar_image.min())
    normalized = (normalized * 255).astype(np.uint8)

    # GLCM матрица
    glcm = graycomatrix(normalized, distances=[1], angles=[0],
                       symmetric=True, normed=True)

    # Текстурные метрики
    contrast = graycoprops(glcm, 'contrast')[0, 0]
    homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
    energy = graycoprops(glcm, 'energy')[0, 0]

    return contrast, homogeneity, energy
```

### 4. Морфологический анализ

#### Форма и структура:
- **Ледниковые зоны**: Обычно имеют более регулярную форму
- **Обломочные зоны**: Более фрагментированные, хаотичные

#### Методы:
```python
def morphological_analysis(binary_mask):
    """
    Морфологический анализ для очистки масок
    """
    from scipy.ndimage import binary_opening, binary_closing, label

    # Удаление шумов
    cleaned = binary_opening(binary_mask, structure=np.ones((3,3)))
    cleaned = binary_closing(cleaned, structure=np.ones((3,3)))

    # Определение связанных компонент
    labeled, num_features = label(cleaned)

    # Фильтрация по размеру
    min_area = 10  # минимальная площадь компоненты (пиксели)
    large_components = np.zeros_like(cleaned)

    for i in range(1, num_features + 1):
        component = (labeled == i)
        if np.sum(component) >= min_area:
            large_components |= component

    return large_components
```

### 5. Комбинированный подход

#### Интеграция нескольких методов:
```python
def combined_classification(vv_images, vh_images=None, time_series=None):
    """
    Комбинированная классификация ледниковой поверхности
    """
    results = {}

    # 1. Поляризационное отношение (если доступны VH данные)
    if vh_images is not None:
        ice_mask_pol, debris_mask_pol, ratio = classify_ice_vs_debris(
            vv_images[-1], vh_images[-1]
        )
        results['polarization'] = {
            'ice_mask': ice_mask_pol,
            'debris_mask': debris_mask_pol,
            'ratio': ratio
        }

    # 2. Временной анализ (если доступны временные ряды)
    if time_series is not None and len(time_series) > 1:
        stable_mask, variable_mask, std = temporal_classification(time_series)
        results['temporal'] = {
            'stable_mask': stable_mask,
            'variable_mask': variable_mask,
            'std_dev': std
        }

    # 3. Текстурный анализ
    contrast, homogeneity, energy = texture_analysis(vv_images[-1])
    results['texture'] = {
        'smooth_ice': homogeneity > 0.7,  # Высокая однородность = лёд
        'rough_debris': contrast > 0.5   # Высокий контраст = обломки
    }

    # 4. Финальная комбинированная маска
    final_ice_mask = np.zeros_like(vv_images[-1], dtype=bool)

    # Комбинируем результаты
    if 'polarization' in results and 'temporal' in results:
        # Логика комбинирования
        pol_ice = results['polarization']['ice_mask']
        temp_var = results['temporal']['variable_mask']
        final_ice_mask = pol_ice & temp_var

    return results, final_ice_mask
```

---

## 📊 Улучшения для пайплайна

### Обновленная конфигурация (`config.yaml`):

```yaml
# Улучшенная классификация поверхности
classification:
  # Много-поляризационный подход
  use_dual_pol: true  # Использовать VV+VH если доступно
  polarization_ratio_threshold: 7  # dB порог для VV/VH отношения

  # Временной анализ
  temporal_stability_threshold: 2  # dB порог стабильности
  min_time_series_length: 3  # минимум изображений для анализа

  # Текстурный анализ
  texture_window_size: 5  # размер окна для GLCM
  texture_contrast_threshold: 0.5  # порог контраста

  # Морфологическая обработка
  min_component_area: 10  # пикселей
  morphological_opening: true
  morphological_closing: true

  # Классы поверхности
  surface_classes:
    - "clean_ice"           # Чистый лёд
    - "debris_covered_ice"  # Лёд под обломками
    - "rock_debris"         # Камни и обломки
    - "wet_snow"           # Мокрый снег
    - "dry_snow"           # Сухой снег
    - "water"              # Вода
```

### Обновленный пайплайн (`sar_pipeline.py`):

```python
class ImprovedSARGlacierPipeline(SARGlacierPipeline):
    """
    Улучшенный пайплайн с классификацией обломочного покрова
    """

    def classify_glacier_surfaces(self, sar_images, dates,
                                  use_dual_pol=False, vh_images=None):
        """
        Классификация типов поверхности ледника

        Args:
            sar_images: Список VV изображений
            dates: Соответствующие даты
            use_dual_pol: Использовать ли кросс-поляризацию
            vh_images: VH изображения (если доступны)
        """
        logger.info("Starting improved surface classification...")

        results = {}

        # 1. Базовая классификация по порогу
        baseline_mask = self.detect_glacier_boundaries(sar_images[-1])

        # 2. Поляризационный анализ (если доступны VH данные)
        if use_dual_pol and vh_images is not None:
            pol_results = self._polarization_classification(
                sar_images[-1], vh_images[-1]
            )
            results['polarization'] = pol_results

        # 3. Временной анализ
        if len(sar_images) > 2:
            temp_results = self._temporal_classification(sar_images, dates)
            results['temporal'] = temp_results

        # 4. Текстурный анализ
        text_results = self._texture_classification(sar_images[-1])
        results['texture'] = text_results

        # 5. Комбинированная классификация
        final_classification = self._combine_classifications(results)

        return results, final_classification

    def _polarization_classification(self, vv_image, vh_image):
        """Поляризационный анализ для различения льда и обломков"""
        ratio = vv_image / (vh_image + 1e-10)
        ratio_db = 10 * np.log10(ratio + 1e-10)

        # Пороги для классификации
        ice_threshold = 7  # dB
        debris_threshold = 3  # dB

        ice_mask = ratio_db > ice_threshold
        debris_mask = (ratio_db >= debris_threshold) & (ratio_db <= ice_threshold)
        uncertain_mask = ratio_db < debris_threshold

        return {
            'ratio_db': ratio_db,
            'ice_mask': ice_mask,
            'debris_mask': debris_mask,
            'uncertain_mask': uncertain_mask
        }

    def _temporal_classification(self, images, dates):
        """Временной анализ для выявления стабильных/переменных зон"""
        # Создать временные ряды для каждого пикселя
        time_series = np.stack(images, axis=0)

        # Стандартное отклонение
        std_dev = np.std(time_series, axis=0)

        # Коэффициент вариации
        mean_val = np.mean(time_series, axis=0)
        cv = std_dev / (mean_val + 1e-10)

        # Пороги
        stable_threshold = 2  # dB
        variable_threshold = 0.15  # коэффициент вариации

        stable_mask = std_dev < stable_threshold
        variable_mask = cv > variable_threshold

        return {
            'std_dev': std_dev,
            'cv': cv,
            'stable_mask': stable_mask,
            'variable_mask': variable_mask
        }

    def _texture_classification(self, image):
        """Текстурный анализ для различения поверхностей"""
        from skimage.feature import graycomatrix, graycoprops

        # Нормализация
        normalized = (image - image.min()) / (image.max() - image.min())
        normalized = (normalized * 255).astype(np.uint8)

        # GLCM
        glcm = graycomatrix(normalized, distances=[1], angles=[0],
                           symmetric=True, normed=True)

        # Метрики текстуры
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
        energy = graycoprops(glcm, 'energy')[0, 0]

        # Классификация
        smooth_ice = homogeneity > 0.7
        rough_debris = contrast > 0.5

        return {
            'contrast': contrast,
            'homogeneity': homogeneity,
            'energy': energy,
            'smooth_ice_mask': smooth_ice,
            'rough_debris_mask': rough_debris
        }

    def _combine_classifications(self, results):
        """Комбинирование результатов классификации"""
        # Начальная маска
        combined_mask = np.zeros_like(list(results.values())[0]['ice_mask'], dtype=int)

        # Приоритизация методов
        weights = {
            'polarization': 0.4,
            'temporal': 0.3,
            'texture': 0.3
        }

        # Комбинирование
        for method, weight in weights.items():
            if method in results:
                method_result = results[method]

                if method == 'polarization':
                    mask = method_result['ice_mask'].astype(int)
                elif method == 'temporal':
                    mask = method_result['variable_mask'].astype(int)
                elif method == 'texture':
                    mask = method_result['smooth_ice_mask'].astype(int)

                combined_mask += (mask * weight)

        # Финальная классификация
        final_ice_mask = combined_mask > 0.5

        return {
            'combined_score': combined_mask,
            'ice_mask': final_ice_mask,
            'confidence': combined_mask
        }
```

---

## 📈 Практические рекомендации

### 1. Используйте dual-pol данные
- Скачивайте продукты Sentinel-1 с VV+VH поляризацией
- Это дает дополнительную информацию для классификации

### 2. Собирайте временные ряды
- Минимум 3-4 изображения в разные сезоны
- Лето + зима для анализа сезонных изменений

### 3. Валидация результатов
- Сравнивайте с оптическими данными (Landsat/Sentinel-2)
- Используйте DEM для анализа топографии
- Проводите полевые измерения при возможности

### 4. Настройка порогов
- Адаптируйте пороги под конкретный регион
- Тестируйте на известных областях
- Учитывайте локальные условия (влажность, тип обломков)

---

## 🎓 Научные источники

1. **Nagler et al. (2015)** - "Retrieval of wet snow by means of multitemporal SAR data"
   - Показали эффективность VV/VH отношения для различения поверхностей

2. **Winsvold et al. (2018)** - "Using SAR satellite data time series for regional glacier mapping"
   - Доказали ценность временного анализа для классификации

3. **Paul et al. (2016)** - "The glaciers climate change initiative"
   - Разработали методы для мониторинга ледников с обломочным покровом

4. **Huang et al. (2011)** - Исследование, упомянутое в вашем проекте
   - Вероятно, использует комбинацию методов для различения поверхностей

---

## 💡 Для вашего проекта

### Рекомендации для Ala-Archa:

1. **Используйте dual-pol данные** Sentinel-1 (VV+VH)
2. **Соберите временные ряды** минимум за 2-3 года
3. **Примените комбинированный подход** (поляризация + время + текстура)
4. **Настройте пороги** на основе известных зон ледников
5. **Валидируйте** с оптическими данными или полевыми измерениями

### Ожидаемые улучшения:
- **Точность классификации**: +20-30% по сравнению с простым пороговым методом
- **Надежность мониторинга**: Лучшее отслеживание динамики ледников
- **Научная ценность**: Более детальный анализ для публикации

---

## 🔧 Реализация в коде

### Шаги интеграции:

1. **Обновите конфигурацию** в `config.yaml`
2. **Используйте улучшенный пайплайн** `ImprovedSARGlacierPipeline`
3. **Тестируйте на ваших данных** с визуализацией результатов
4. **Настройте пороги** для оптимальной классификации

Этот подход значительно улучшит способность различать ледниковые поверхности от обломочного покрова в ваших SAR данных!

---

**Команда TengriSpacers**  
**NASA Space Apps Challenge 2025**  
**Challenge: Through the Radar Looking Glass**


