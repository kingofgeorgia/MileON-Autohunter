# Обновление локаций - 12 февраля 2026

## Проблема
Локации отображались как ID номера вместо названий во всех частях системы:
- Telegram bot использовал устаревший хардкодированный словарь (62 локации)
- Parser выводил location_id без названия
- GUI не показывал названия локаций

## Решение

### 1. Создан sync_locations.py
Скрипт для загрузки актуальных локаций из официального MyAuto API:
- Загружает 93 локации через `MyAutoAPI.get_locations()`
- Создает два JSON файла:
  - `locations.json` - словарь {id: name} для быстрого доступа
  - `locations_full.json` - полные данные с metadata

**Результат:**
```
✅ Saved 93 locations
Примеры:
  2: Tbilisi
  3: Kutaisi
  4: Batumi
  ...
```

### 2. Обновлен telegram_bot.py
**До:**
```python
LOCATIONS = {
    1: "tbilisi", 2: "gori", 3: "zugdidi", ...  # 62 локации
}
```

**После:**
```python
def load_locations():
    locations_path = Path(__file__).parent / "locations.json"
    if locations_path.exists():
        with locations_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

LOCATIONS = load_locations()  # 93 локации
```

### 3. Обновлен parser.py
**Изменения:**
- Добавлена функция `load_locations()` для загрузки из JSON
- Добавлено поле `location_name` в parsed data
- Print statements показывают название вместо ID
- Output файлы содержат названия локаций

**До:**
```python
print(f"  🚗 {car['model']} | 📍 Локация {car['location']}")  # ID
```

**После:**
```python
location_display = LOCATIONS.get(car.get('location'), f"ID:{car.get('location')}")
print(f"  🚗 {car['model']} | 📍 {location_display}")  # Tbilisi
```

### 4. Обновлен mileon_saas/gui/main.py
**Изменения:**
- Добавлена функция `load_locations()` для загрузки из JSON
- Обновлены все три источника данных:
  - API listings (combined_tree)
  - Local JSON data (local_tree)
  - Combined view (сводная таблица)

**Преобразование ID в названия:**
```python
location_id = item.get("location") or ""
location_name = LOCATIONS.get(location_id, location_id) if location_id else ""
```

## Результаты

### Покрытие локаций
| Было | Стало |
|------|-------|
| 62 хардкод | 93 из API |
| Устаревшие транслитерации | Официальные английские названия |
| Устаревшие ID | Актуальные данные |

### Обновленные файлы
✅ `sync_locations.py` - новый скрипт синхронизации
✅ `locations.json` - актуальный справочник (93 локации)
✅ `locations_full.json` - полные данные
✅ `telegram_bot.py` - загрузка из JSON
✅ `parser.py` - отображение названий + location_name в данных
✅ `mileon_saas/gui/main.py` - отображение названий во всех таблицах
✅ `test_locations.py` - тестовый скрипт

### Использование

**Обновление локаций:**
```bash
python sync_locations.py
```

**Автоматическая работа:**
Все модули загружают `locations.json` при старте через `load_locations()`.

**Fallback на ID:**
Если локация не найдена в справочнике:
```python
LOCATIONS.get(location_id, f"ID:{location_id}")  # -> "ID:999"
```

## Интеграция с myauto_api.py

sync_locations.py использует комплексный API client:
```python
from myauto_api import MyAutoAPI

api = MyAutoAPI()
locations = api.get_locations()  # List[Location]
```

Каждая локация:
```python
@dataclass
class Location:
    location_id: int
    title: str  # Tbilisi, Kutaisi, etc.
```

## Технические детали

### Encoding
Все файлы используют `encoding='utf-8'` для корректной обработки Unicode символов.

### Type Conversion
ID из JSON всегда преобразуются в int:
```python
return {int(k): v for k, v in data.items()}
```

### Path Resolution
```python
# telegram_bot.py & parser.py
Path(__file__).parent / "locations.json"

# GUI
Path(__file__).parent.parent.parent / "locations.json"
```

## Тестирование

Запущен `test_locations.py`:
```
✅ Загружено 93 локаций

Тест преобразования ID -> Название:
  2 -> Tbilisi
  3 -> Kutaisi
  4 -> Batumi
  999 -> ID:999  # Fallback
```

## Следующие шаги

1. ✅ Регулярное обновление через `python sync_locations.py`
2. ✅ Интеграция во все модули завершена
3. ✅ Английские названия загружаются автоматически (language="en")
4. 🔄 Можно добавить cron для автоматического обновления

---

**Статус:** ✅ Все локации правильно отображаются во всех частях системы
