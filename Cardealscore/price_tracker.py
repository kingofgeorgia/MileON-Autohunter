"""
Модуль для отслеживания изменений цен и новых авто
"""
import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = "cars_history.json"

def load_previous_data():
    """
    Загрузить данные предыдущего запуска
    """
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"cars": {}, "last_update": None}
    return {"cars": {}, "last_update": None}

def save_current_data(cars_list):
    """
    Сохранить текущие данные как историю
    """
    cars_dict = {}
    for car in cars_list:
        car_id = str(car['car_id'])
        cars_dict[car_id] = {
            'price_usd': car['price_usd'],
            'year': car['year'],
            'engine_volume': car['engine_volume'],
            'model': car['model'],
            'rating': car.get('rating', 0),
            'date': car['date'],
            'phone': car['phone'],
            'location': car['location'],
            'photo_url': car['photo_url'],
            'description': car['description']
        }
    
    history = {
        "cars": cars_dict,
        "last_update": datetime.now().isoformat()
    }
    
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def find_changes(current_cars, previous_data):
    """
    Найти новые авто и изменения цен
    """
    previous_cars = previous_data.get("cars", {})
    
    new_good_cars = []  # Новые авто с рейтингом > 70
    price_drops = []     # Авто с упавшей ценой
    
    current_ids = set(str(c['car_id']) for c in current_cars)
    previous_ids = set(previous_cars.keys())
    
    # Ищем новые авто
    new_ids = current_ids - previous_ids
    for car in current_cars:
        car_id = str(car['car_id'])
        if car_id in new_ids and car.get('rating', 0) > 70:
            new_good_cars.append(car)
    
    # Ищем снижение цены
    for car in current_cars:
        car_id = str(car['car_id'])
        if car_id in previous_ids:
            old_price = previous_cars[car_id]['price_usd']
            new_price = car['price_usd']
            
            # Если цена упала на 5% или более
            if old_price > 0:
                drop_percent = ((old_price - new_price) / old_price) * 100
                if drop_percent >= 5:  # 5% порог
                    price_drops.append({
                        'car': car,
                        'old_price': old_price,
                        'drop_percent': drop_percent
                    })
    
    return new_good_cars, price_drops

if __name__ == "__main__":
    print("Модуль отслеживания загружен успешно")
