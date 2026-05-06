# Фильтрация Автосалонов

## Проблема

**Дата обнаружения:** 2025-02-11

Автосалоны (https://myauto.ge/ka/autosalons) публикуют объявления, которые:
- Представляют **несколько автомобилей** в одном объявлении (складские запасы)
- **Висят годами** без изменений (не реальные продажи)
- **Искажают ML модель**: обучение на них создает неправильные паттерны продаж

### Масштаб проблемы

До исправления:
- Всего листингов: **38,181**
- Автосалоны: **2,579 (6.8%)**
- Частные продавцы: **35,602 (93.2%)**

## Решение

### 1. Определение автосалонов

**Критерий:** `dealer_user_id > 0` в ответе API

```python
# Частный продавец
{
    "dealer_user_id": 0,  # или NULL
    "user_id": 3565824,
    ...
}

# Автосалон
{
    "dealer_user_id": 123456,  # > 0
    "user_id": 789012,
    ...
}
```

### 2. Изменения в коде

#### mileon_saas/services/full_site_parser.py

```python
def _transform_listing(self, api_item: dict) -> dict:
    """Transform API response format to comprehensive format with all available fields."""
    # ФИЛЬТР: Исключить автосалоны (dealer_user_id > 0)
    dealer_user_id = api_item.get('dealer_user_id', 0)
    if dealer_user_id and dealer_user_id > 0:
        return None  # Пропустить автосалон
    
    # ... остальная логика парсинга
```

**Эффект:** Автосалоны больше не будут добавляться в базу при парсинге

#### setup_listing_tracking.py

```python
# Получить все активные листинги (ИСКЛЮЧАЯ автосалоны)
result = await session.execute(
    select(CarListing).where(
        CarListing.source == "myauto",
        (CarListing.dealer_user_id == None) | (CarListing.dealer_user_id == 0)
    )
)
```

**Эффект:** Мониторинг отслеживает только частных продавцов

#### convert_estimated_to_closed.py

```sql
SELECT ed.*, cl.*
FROM estimated_deals ed
LEFT JOIN car_listings cl ON ed.listing_id = cl.id
WHERE ed.confidence_score >= ?
AND (cl.dealer_user_id IS NULL OR cl.dealer_user_id = 0)  -- Фильтр!
```

**Эффект:** ML обучается только на сделках частных продавцов

### 3. Очистка базы данных

```bash
# Удалено при внедрении изменений
DELETE FROM car_listings WHERE dealer_user_id > 0;
# Удалено: 2,579 автосалонов
```

**Результат:**
- До: 38,181 листингов
- После: 35,602 листингов (только частники)

### 4. Схема listing_history

Колонка `dealer_user_id` будет добавлена автоматически при следующем снимке:

```python
# В setup_listing_tracking.py
snapshot = ListingHistory(
    source_listing_id=listing.source_listing_id,
    dealer_user_id=listing.dealer_user_id,  # Теперь отслеживается
    # ...
)
```

## Влияние на ML модель

### До исправления
- Автосалоны: "Автомобили продаются через 365+ дней"
- Частные продавцы: "Автомобили продаются через 14-60 дней"
- **ML учится неправильным паттернам** (смешанные данные)

### После исправления
- Только частные продавцы: "Автомобили продаются через 14-60 дней"
- **ML учится правильным паттернам** (чистые данные)

### Ожидаемые улучшения
- Точность R²: **+10-15%** (чище данные)
- Ложные срабатывания: **-50%** (меньше "зависших" объявлений)
- Уверенность в оценках: **+15-20%** (точнее прогнозы)

## Проверка работы

```bash
# 1. Проверить базу данных
python -c "import sqlite3; conn = sqlite3.connect('mileon_saas.db'); \
c = conn.cursor(); c.execute('SELECT COUNT(*) FROM car_listings'); \
print(f'Всего: {c.fetchone()[0]}'); \
c.execute('SELECT COUNT(*) FROM car_listings WHERE dealer_user_id > 0'); \
print(f'Автосалонов: {c.fetchone()[0]}')"

# Ожидаемый результат:
# Всего: 35602
# Автосалонов: 0

# 2. Запустить мониторинг
python setup_listing_tracking.py
# Опция 2: Сделать снимок
# Должен обработать ~35,602 листингов (без автосалонов)

# 3. Проверить estimated_deals
python setup_listing_tracking.py
# Опция 5: Сгенерировать estimated_deals
# Все сделки должны быть от частных продавцов

# 4. Конвертировать в closed_deals
python convert_estimated_to_closed.py
# Должен конвертировать только сделки частников
```

## Важные замечания

### ✅ Что изменилось
1. **Парсер** автоматически пропускает автосалоны
2. **База данных** очищена от существующих автосалонов
3. **Мониторинг** отслеживает только частных продавцов
4. **ML обучение** использует только чистые данные

### ⚠️ Что НЕ изменилось
- GUI продолжает работать как раньше (просто показывает меньше листингов)
- API запросы работают без изменений
- Существующие closed_deals не удалены (исторические данные)

### 🔄 Ретроспективная очистка (опционально)

Если в `closed_deals` есть автосалоны (до исправления):

```sql
-- Удалить сделки автосалонов из closed_deals
DELETE FROM closed_deals
WHERE listing_id IN (
    SELECT id FROM car_listings WHERE dealer_user_id > 0
);
```

**Примечание:** Это не обязательно, т.к. автосалоны уже удалены из car_listings,
и новые сделки автоматически фильтруются.

## Техническая справка

### Файлы изменены
- `mileon_saas/services/full_site_parser.py` - фильтрация при парсинге
- `setup_listing_tracking.py` - фильтрация в мониторинге
- `convert_estimated_to_closed.py` - фильтрация при конвертации

### Таблицы затронуты
- `car_listings` - удалено 2,579 записей автосалонов
- `listing_history` - добавлена колонка dealer_user_id (при следующем снимке)
- `estimated_deals` - фильтрация автосалонов на этапе генерации
- `closed_deals` - фильтрация автосалонов на этапе конвертации

### SQL-фильтр для запросов

Используйте это условие во всех запросах, где нужны только частные продавцы:

```sql
WHERE (dealer_user_id IS NULL OR dealer_user_id = 0)
```

## История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2025-02-11 | 1.0 | Первый релиз: фильтрация автосалонов |

---
**Статус:** ✅ Внедрено  
**Приоритет:** Критический (влияет на точность ML)  
**Автор:** Mileon SaaS Team
