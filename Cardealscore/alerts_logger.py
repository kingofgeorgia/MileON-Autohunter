"""
Логирование алертов в файл (если Telegram недоступен)
"""
import json
from datetime import datetime

ALERTS_FILE = "alerts_log.json"

def log_alert(alert_type, data):
    """
    Логировать алерт в файл
    """
    try:
        # Загружаем существующие алерты
        try:
            with open(ALERTS_FILE, "r", encoding='utf-8') as f:
                alerts = json.load(f)
        except:
            alerts = []
        
        # Добавляем новый алерт
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "data": data
        }
        alerts.append(alert)
        
        # Сохраняем
        with open(ALERTS_FILE, "w", encoding='utf-8') as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Алерт сохранён: {alert_type}")
        return True
    except Exception as e:
        print(f"❌ Ошибка логирования алерта: {e}")
        return False

def log_new_car(car):
    """Логировать новое хорошее авто"""
    return log_alert("new_good_car", {
        "car_id": car['car_id'],
        "model": car['model'],
        "price": car['price_usd'],
        "year": car['year'],
        "rating": car.get('rating', 0)
    })

def log_price_drop(car, old_price):
    """Логировать снижение цены"""
    drop_percent = ((old_price - car['price_usd']) / old_price) * 100
    return log_alert("price_drop", {
        "car_id": car['car_id'],
        "model": car['model'],
        "old_price": old_price,
        "new_price": car['price_usd'],
        "drop_percent": drop_percent
    })

if __name__ == "__main__":
    print("Модуль логирования алертов загружен")
