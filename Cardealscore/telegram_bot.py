"""
Модуль для отправки сообщений в Telegram
"""
import json
import requests
from datetime import datetime
from pathlib import Path
import re
import os
# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", "")).strip()
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0") or 0)
# ======================================================

# Загружаем локации из JSON
def load_locations():
    """Загружает локации из locations.json."""
    locations_path = Path(__file__).parent / "locations.json"
    if locations_path.exists():
        with locations_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # Преобразуем ID в int
            return {int(k): v for k, v in data.items()}
    return {}

LOCATIONS = load_locations()

# Маппинг типов топлива (ID -> Название)
FUEL_TYPES = {
    1: "petrol", 2: "diesel", 3: "hybrid", 4: "electric", 5: "lpg", 6: "cng"
}

def generate_listing_url(car):
    """
    Генерирует правильный URL для объявления на myauto.ge
    Формат: https://myauto.ge/en/pr/{car_id}/{slug}?offerType=vipPlus&source=search
    """
    car_id = car.get('car_id', '')
    
    # Собираем части слага
    slug_parts = ['for-sell', 'cars']
    
    # Добавляем модель (если есть)
    model = car.get('model', '').strip()
    if model:
        # Очищаем модель и преобразуем в дефисное написание
        model_slug = re.sub(r'[^a-z0-9\s-]', '', model.lower())
        model_slug = re.sub(r'\s+', '-', model_slug)
        slug_parts.append(model_slug)
    
    # Добавляем год
    year = car.get('year', '')
    if year:
        slug_parts.append(str(year))
    
    # Добавляем тип топлива (если есть)
    fuel_type_id = car.get('fuel_type', '')
    if fuel_type_id and fuel_type_id in FUEL_TYPES:
        slug_parts.append(FUEL_TYPES[fuel_type_id])
    
    # Добавляем локацию (если есть)
    location_id = car.get('location', '')
    if location_id and location_id in LOCATIONS:
        slug_parts.append(LOCATIONS[location_id])
    
    # Собираем финальный слаг
    slug = '-'.join(slug_parts)
    
    # Формируем URL
    return f"https://myauto.ge/en/pr/{car_id}/{slug}?offerType=vipPlus&source=search"

def send_message(text, parse_mode="HTML"):
    """
    Отправить сообщение в Telegram
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram is not configured: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram: сообщение отправлено")
            return True
        else:
            print(f"❌ Telegram ошибка: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram ошибка подключения: {e}")
        return False

def send_new_car_alert(car):
    """
    Алерт о новом хорошем автомобиле
    """
    listing_url = generate_listing_url(car)
    
    text = f"""
🔥 <b>НОВОЕ ОТЛИЧНОЕ ПРЕДЛОЖЕНИЕ!</b>

🏆 Рейтинг: <b>{car.get('rating', 0):.1f}/100</b>

💰 Цена: <b>${car['price_usd']}</b>
📅 Год: <b>{car['year']}</b>
⚙️ Объем: <b>{car['engine_volume']} ccm</b>
🚗 Модель: <b>{car['model']}</b>
📍 Локация: {car['location']}

📸 Фото: {car['photo_url']}
🔗 <a href="{listing_url}">Посмотреть объявление</a>
🆔 ID: {car['car_id']}

📝 Описание: {car['description'][:100]}...
"""
    return send_message(text)

def send_price_drop_alert(car, old_price):
    """
    Алерт о снижении цены
    """
    price_drop = old_price - car['price_usd']
    drop_percent = (price_drop / old_price) * 100
    listing_url = generate_listing_url(car)
    
    text = f"""
📉 <b>ЦЕНА УПАЛА!</b>

🏆 Рейтинг: <b>{car.get('rating', 0):.1f}/100</b>

💰 <s>${old_price}</s> → <b>${car['price_usd']}</b> 
(-${price_drop} или {drop_percent:.1f}%)

📅 Год: <b>{car['year']}</b>
⚙️ Объем: <b>{car['engine_volume']} ccm</b>
🚗 Модель: <b>{car['model']}</b>

📸 Фото: {car['photo_url']}
🔗 <a href="{listing_url}">Посмотреть объявление</a>
🆔 ID: {car['car_id']}
"""
    return send_message(text)

def send_summary(total, new_cars, price_drops, top_cars):
    """
    Отправить сводку по найденным авто
    """
    text = f"""
📊 <b>ОТЧЁТ ПО ЗАКУПКАМ ({datetime.now().strftime('%Y-%m-%d %H:%M')})</b>

📈 Всего авто на рынке: <b>{total}</b>

🆕 Новых хороших авто (рейтинг >70): <b>{len(new_cars)}</b>
📉 Цены упали: <b>{len(price_drops)}</b>

🏆 <b>ТОП 5 ПО РЕЙТИНГУ:</b>
"""
    
    for idx, car in enumerate(top_cars[:5], 1):
        text += f"\n#{idx} {car['model']} - ${car['price_usd']} (рейтинг {car.get('rating', 0):.1f})"
    
    return send_message(text)

if __name__ == "__main__":
    # Тест
    print("Проверка подключения к Telegram...")
    test_msg = send_message("<b>✅ Бот подключен и работает!</b>")
    if test_msg:
        print("✅ Telegram работает корректно")
    else:
        print("❌ Ошибка подключения к Telegram")
