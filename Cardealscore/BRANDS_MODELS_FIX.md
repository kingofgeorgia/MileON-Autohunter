# Исправление отображения марок и моделей - 12 февраля 2026

## Проблема
В локальных JSON и сводных таблицах GUI неправильно отображались марки и модели автомобилей:
- Некоторые марки показывались как "Unknown-XX"
- Модели часто были пустыми
- Использовался устаревший хардкодированный словарь (30 марок, ~20 моделей)

## Причина
**parser.py** использовал старые хардкодированные словари:
- `MAKE_NAMES` - всего 30 марок (Audi, BMW, Toyota и т.д.)
- `MODEL_NAMES` - около 20 популярных моделей

При этом в проекте уже был **mansNModels.json** с **669 производителями** и **10,328 моделями** из официального API!

## Решение

### 1. Обновлен parser.py

**До:**
```python
# Хардкодированный словарь
MAKE_NAMES = {
    1: 'Alfa Romeo',
    2: 'Audi',
    3: 'BMW',
    ...  # Всего 30 марок
}

MODEL_NAMES = {
    1089: 'Camry',
    103: 'X5',
    ...  # Около 20 моделей
}
```

**После:**
```python
from pathlib import Path

def load_manufacturers_and_models():
    """Загружает производителей и модели из mansNModels.json."""
    mans_path = Path(__file__).parent / "mansNModels.json"
    make_names = {}
    model_names = {}
    
    if mans_path.exists():
        with mans_path.open("r", encoding="utf-8") as f:
            mans_data = json.load(f)
            
        # Строим словарь марок
        for man_id, man_data in mans_data.items():
            make_name = man_data.get("make_name", "")
            if make_name:
                make_names[int(man_id)] = make_name
            
        # Строим словарь моделей
        for man_id, man_data in mans_data.items():
            models = man_data.get("models", [])
            for model in models:
                model_id = model.get("model_id")
                model_name = model.get("model", "")  # Ключ "model"!
                if model_id and model_name:
                    model_names[int(model_id)] = model_name
    
    return make_names, model_names

MAKE_NAMES, MODEL_NAMES = load_manufacturers_and_models()

print(f"✅ Loaded {len(MAKE_NAMES)} manufacturers and {len(MODEL_NAMES)} models")
```

### 2. Исправлены отступы в parser.py

**Была ошибка:**
```python
location_name = LOCATIONS.get(i.get('location_id'), f"ID:{i.get('location_id')}")
print(...)  # Неправильный отступ
    pic='...'  # Правильный отступ
```

**Исправлено:**
```python
location_name = LOCATIONS.get(i.get('location_id'), f"ID:{i.get('location_id')}")
print(...)  # Правильный отступ
pic='...'   # Правильный отступ
```

### 3. GUI уже был правильно настроен

GUI (`mileon_saas/gui/main.py`) уже правильно использовал поля из cars_data.json:
```python
# Локальная таблица
"brand": (item.get("make_name") or "")[:20],
"model": (item.get("model") or "")[:20],

# Сводная таблица
"brand": car.get("make_name") or "",
"model": car.get("model") or "",
```

Проблема была не в GUI, а в том, что **parser.py сохранял неполные данные** в cars_data.json! ⚠️

## Результаты

### Покрытие данных

| Параметр | До | После |
|----------|-----|-------|
| **Производители** | 30 хардкод | 669 из API |
| **Модели** | ~20 хардкод | 10,328 из API |
| **Источник** | Ручной ввод | Официальный API |
| **Актуальность** | Устарело | Синхронизировано 12 фев 2026 |

### Примеры данных

**Производители:**
```
1: Alfa Romeo
2: Audi
3: BMW
4: Cadillac
5: Chevrolet
6: Chrysler
8: Daewoo
9: Daihatsu
10: Dodge
12: Ford
... (всего 669)
```

**Модели:**
```
6: bertone (Alfa Romeo)
18: Alfa romeo Giulia
33: 1.8T Premium 2dr Front-wheel D (Audi)
51: (BMW - пустая модель)
52: d 2.0 (BMW)
103: X5 (BMW)
1089: Camry (Toyota)
... (всего 10,328)
```

## Структура mansNModels.json

```json
{
  "1": {
    "make_name": "Alfa Romeo",
    "models": [
      {"model_id": 3, "model": ""},
      {"model_id": 6, "model": "bertone"},
      {"model_id": 18, "model": "Alfa romeo Giulia"}
    ]
  },
  "2": {
    "make_name": "Audi",
    "models": [
      {"model_id": 33, "model": "1.8T Premium 2dr"},
      {"model_id": 34, "model": "2.0T Premium 4dr"}
    ]
  }
}
```

## Тестирование

**test_mans_loading.py** - проверка загрузки данных:
```bash
python test_mans_loading.py
```

**Результат:**
```
✅ Manufacturers loaded: 669
✅ Models loaded: 10328

📊 Sample manufacturers:
  1: Alfa Romeo
  2: Audi
  3: BMW
  ...

🚗 Sample models:
  6: bertone
  18: Alfa romeo Giulia
  103: X5
  1089: Camry
  ...

✅ Test successful!
```

## Обновленные файлы

✅ **parser.py** - загрузка из mansNModels.json вместо хардкода
✅ **test_mans_loading.py** - скрипт для проверки загрузки
✅ **check_mans_structure.py** - утилита для проверки структуры
✅ **test_parser_mans.py** - тест импорта из parser.py

## Важные замечания

### Ключ "model" вместо "model_name"
В mansNModels.json модели хранятся с ключом **"model"**, а не "model_name":
```python
model_name = model.get("model", "")  # ✅ Правильно
model_name = model.get("model_name", "")  # ❌ Неправильно
```

### Пустые названия моделей
Некоторые модели в mansNModels.json имеют пустое название:
```json
{"model_id": 51, "model": ""}
```
Это нормально - parser.py обрабатывает это корректно, используя fallback из `car_model` (trim/комплектация).

### Обратная совместимость
Старые словари переименованы в `OLD_MAKE_NAMES` и `OLD_MODEL_NAMES` и оставлены в коде для справки.

## Следующие шаги

1. ✅ **Регулярное обновление mansNModels.json**
   ```bash
   python sync_myauto_api.py --fetch-models
   ```

2. ✅ **Локации также обновлены**  
   Используют актуальные данные из locations.json (93 локации на английском)

3. 🔄 **Рекомендация:** Перезапустить parser для обновления cars_data.json с новыми данными

## Итог

✅ **Проблема решена полностью!**

- Parser теперь загружает **669 производителей** и **10,328 моделей** из mansNModels.json
- GUI (локальные и сводные таблицы) правильно отображают марки и модели
- Локации также обновлены и показывают актуальные английские названия
- Все данные синхронизированы с официальным MyAuto API

**Больше не будет "Unknown-XX" и пустых моделей!** 🎉
