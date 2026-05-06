# myauto.ge Car Market Monitor

Приложение для мониторинга цен и отслеживания хороших предложений автомобилей на грузинском автомобильном рынке (myauto.ge) с отправкой алертов в Telegram и визуальным интерфейсом.

## 🎯 Функциональность

- **📊 Графический интерфейс**: Красивая таблица со всеми автомобилями с сортировкой и фильтрацией
- **🔍 Умные фильтры**: Фильтрация по модели, цене, году выпуска и рейтингу
- **⭐ Рейтинговая система**: Автоматический расчет рейтинга автомобилей (цена 40%, год 35%, объем двигателя 25%)
- **📱 Telegram алерты**: Отправка уведомлений о новых хороших предложениях и снижении цен
- **🔄 Автоматическое обновление**: Кнопка обновления для запуска парсера прямо из приложения
- **💾 История отслеживания**: Сохранение истории цен и отслеживание изменений
- **🔗 Правильные ссылки**: Генерация корректных ссылок на объявления в myauto.ge

## 📋 Структура проекта

### Основные компоненты

1. **app.py** - Графический интерфейс (главное приложение)
   - Таблица всех доступных автомобилей
   - Фильтры в реальном времени
   - Кнопка "Обновить парсер" для запуска парсера
   - Кнопка копирования ссылки на выбранный автомобиль

2. **parser.py** - Основной парсер
   - Загружает данные с API myauto.ge
   - Считает рейтинг для каждого автомобиля
   - Отслеживает новые хорошие предложения (рейтинг > 70)
   - Отслеживает снижение цены (≥ 5%)
   - Отправляет алерты в Telegram

3. **telegram_bot.py** - Интеграция с Telegram
   - Отправка сообщений в Telegram
   - Генерация правильных ссылок на объявления
   - Форматированные сообщения с эмодзи и ссылками

4. **price_tracker.py** - Отслеживание цен
   - Сравнение текущих и исторических данных
   - Определение новых хороших автомобилей
   - Обнаружение снижения цены

5. **alerts_logger.py** - Логирование алертов
   - Сохранение алертов в JSON файл (на случай ошибок Telegram)

## 🚀 Запуск

### ✅ Быстрый старт

**Вариант 1: Батник (самый простой)**

Двойной клик на `start.bat` - приложение автоматически запустит визуальный интерфейс.

**Вариант 2: Терминал**

```bash
python app.py
```

**Вариант 3: С парсером в фоне**

```bash
python main.py
```

## 🔧 Установка

### Требования
- Python 3.8+
- Windows (+ работает на Linux/Mac)

### Настройка

1. Клонируем репозиторий:
```bash
git clone https://github.com/kingofgeorgia/mileon_parsing.git
cd mileon_parsing
```

2. Создаем виртуальное окружение:
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Устанавливаем зависимости:
```bash
pip install -r requirements.txt
```

4. Конфигурируем Telegram (в `telegram_bot.py`):
```python
BOT_TOKEN = "ВАШ_TOKEN_БОТА"
CHAT_ID = ВАШ_CHAT_ID
```

5. Запускаем приложение:
```bash
python app.py
```

Get your Telegram API credentials at [https://my.telegram.org/apps](https://my.telegram.org/apps)

## Configuration

Edit the configuration section at the top of each module:

```python
# Telegram API
api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "")
# Channels
SOURCE_CHANNEL = "mileoncars"
TARGET_CHANNEL = "garagesale_dighomi"

# Filtering
CAR_BRANDS = ["BMW", "Mercedes", "Toyota", "Audi", "Porsche"]
CURRENCIES = ["$", "€", "₽", "USD", "EUR"]

# Polling
UPDATE_INTERVAL = 20  # seconds
```

### Filter Configuration

- **CAR_BRANDS**: List of car brands to monitor (case-insensitive)
- **CURRENCIES**: Accepted currency symbols for price detection
- **PRICE_PATTERN**: Regex for price extraction (default: `\d[\d\s]{3,}`)

## Usage

### Run Relay Client
```bash
python parsing.py
```
Continuously monitors source channels and relays matching listings.

## Architecture

```
Telegram Channels (source)
  ↓ (GetHistoryRequest via Telethon)
Channel Messages (raw)
  ↓ (match_filters: brand + price)
Filtered Messages
  ↓ (format_message: markdown + metadata)
Target Channel / Dashboard / API / Notifications
```

### Data Flow

1. **Fetch**: Retrieve latest messages from source channels
2. **Filter**: Match against brand and price criteria (AND condition)
3. **Format**: Convert to markdown with metadata and emoji
4. **Relay**: Post to target channel or dashboard
5. **Deduplicate**: Track message IDs to prevent reposts

## Filtering Logic

Messages must match **both** conditions to be included:
- Contains one of the specified car brands
- Contains a price in the specified currency format

```python
def match_filters(text: str) -> bool:
    if not text:
        return False
    if not any(brand.lower() in text.lower() for brand in CAR_BRANDS):
        return False
    if not PRICE_PATTERN.search(text):
        return False
    return True
```

## Dependencies

```
telethon>=1.0        # Telegram client library
openai>=0.27         # OpenAI integration
```

## Session Management

Each module creates persistent session files:
- `relay_client.session` - Parsing client session
- `session_name.session` - Live monitor session

Sessions preserve authentication. Delete to force re-authentication on next run.

## Troubleshooting

### Session Authentication Issues
Delete the `.session` file and restart the module to re-authenticate via QR code.

### Empty Message History
- Verify channel is public/accessible
- Check API credentials (api_id, api_hash)
- Ensure account has channel access permissions

### Duplicate Posts
The relay client tracks posted message IDs in `posted_ids` set. Clear this to reprocess.

### Telethon Connection Timeouts
The module auto-retries. Check internet connection and Telegram API status.

### Filter Not Working
- Verify CAR_BRANDS contains correct brand names
- Check PRICE_PATTERN regex matches message prices
- Ensure filters use AND logic (both brand AND price required)

## Code Style

- Russian comments throughout (documentation sections)
- Configuration marked with section headers
- Raw strings for regex patterns: `r"pattern"`
- Message text safely accessed via `.text` attribute

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add improvement'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Open a Pull Request

## License

This project is provided as-is for personal use.

## Support

For issues and questions, open an issue on [GitHub](https://github.com/kingofgeorgia/mileon_parsing/issues).
