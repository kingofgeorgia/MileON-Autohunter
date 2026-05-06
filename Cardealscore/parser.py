import requests
import cloudscraper
from fake_useragent import UserAgent
import json
import sys
import os
from pathlib import Path

# Исправляем кодировку для Windows PowerShell
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Импортируем наши модули
from telegram_bot import send_new_car_alert, send_price_drop_alert, send_summary
from price_tracker import load_previous_data, save_current_data, find_changes
from alerts_logger import log_new_car, log_price_drop

# Загружаем локации из JSON
def load_locations():
    """Загружает локации из locations.json."""
    locations_path = Path(__file__).parent / "locations.json"
    if locations_path.exists():
        with locations_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

LOCATIONS = load_locations()

# Загружаем производителей и модели из mansNModels.json
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
            models = man_data.get("models", [])
            for model in models:
                model_id = model.get("model_id")
                model_name = model.get("model", "")  # Используем "model", а не "model_name"
                if model_id and model_name:
                    model_names[int(model_id)] = model_name
    
    return make_names, model_names

MAKE_NAMES, MODEL_NAMES = load_manufacturers_and_models()

print(f"✅ Loaded {len(MAKE_NAMES)} manufacturers and {len(MODEL_NAMES)} models from mansNModels.json")

# Старый хардкодированный словарь (оставлено для справки, не используется)
OLD_MAKE_NAMES = {
    1: 'Alfa Romeo',
    2: 'Audi',
    3: 'BMW',
    5: 'Chevrolet',
    7: 'Ford',
    10: 'Dodge',
    11: 'GMC',
    12: 'Honda',
    14: 'Hyundai',
    16: 'Infiniti',
    18: 'Jaguar',
    19: 'Jeep',
    20: 'Kia',
    22: 'Land Rover',
    23: 'Lexus',
    24: 'Mazda',
    25: 'Mercedes-AMG',
    28: 'MINI',
    29: 'Mitsubishi',
    30: 'Nissan',
    31: 'Opel',
    33: 'Porsche',
    34: 'Renault',
    38: 'Skoda',
    39: 'Subaru',
    41: 'Toyota',
    42: 'Volkswagen',
    43: 'Volvo',
    53: 'Chrysler',
    61: 'Smart',
    75: 'Maserati',
    89: 'BYD',
    110: 'Hummer',
    124: 'Polestar',
    155: 'Tesla',
    161: 'Zeekr',
    394: 'Bentley',
    786: 'Alfa Romeo',
    987: 'Can-Am',
}

# Старый хардкодированный словарь моделей (оставлено для справки, не используется)
OLD_MODEL_NAMES = {
    # Toyota
    1089: 'Camry',
    1128: 'Avalon',
    1124: 'Prius',
    1499: 'Highlander',
    1131: 'Corolla',
    1130: 'RAV4',
    1081: 'Avalon',  # похоже на Avalon по trim
    
    # BMW
    103: 'X5',
    104: 'X3',
    1501: 'X3',  # по trim xDrive35i
    99: '5 Series',
    98: '3 Series',
    108: 'X6',
    68: '5 Series',  # по trim xDrive
    67: '7 Series',
    
    # Mercedes-AMG / Mercedes-Benz
    2239: 'E-Class',
    1814: 'GLE',
    658: 'G-Class',
    1591: 'GLC',
    710: 'S-Class',
    1819: 'GLE',  # по trim GLE 350
    660: 'ML-Class',
    
    # Lexus
    16997: 'RX',
    361: 'ES',
    364: 'GX',
    1640: 'ES',  # по базовому trim
    
    # Jeep
    446: 'Wrangler',
    443: 'Cherokee',
    
    # Tesla
    1994: 'Model 3',
    1995: 'Model Y',
    1993: 'Model S',
    7500: 'Model Y',  # по trim Long Range
    4334: 'Model S',  # по trim Long Range RWD
    
    # Infiniti
    410: 'QX60',
    
    # Hyundai
    2146: 'Tucson',
    344: 'Santa Fe',
    
    # Porsche
    1625: 'Cayenne',
    1707: '911',  # по trim Turbo
    
    # Alfa Romeo
    2101: 'Giulia',
    
    # Honda
    319: 'Pilot',  # по trim Platinum/Titanium
    
    # Dodge
    1559: 'Charger',  # по trim SRT 392
    
    # Volkswagen
    7829: 'ID.4',  # по trim PURE+
}

count=0
UserAgent().chrome
cars_data = []  # Сохраняем полные данные об автомобилях

# Загружаем предыдущие данные для сравнения
previous_data = load_previous_data()
print(f"Загружена история из {previous_data.get('last_update', 'первый запуск')}")

scraper = cloudscraper.create_scraper()  # Создаем scraper для обхода Cloudflare

# vehicleType=0 - Автомобили
base_url = 'https://api2.myauto.ge/en/products?vehicleType=0&ForRent=&Mans=&PriceFrom=600&PriceTo=50000&CurrencyID=1&MileageType=1&Customs=1&Page={}'
for x in range (1,10):
    url = base_url.format(x)
    #print (url)
    request=scraper.get(url, timeout=10)
    print(f"Status: {request.status_code}, Page: {x}")
    if request.status_code != 200:
        continue
    data = request.json()
    for i in data["data"]["items"]:
        if i['engine_volume']>=500 or i['engine_volume']==0:
            print(" ")
            count+=1
            print ('     -======= - ',count,' - =======-    ')
            location_name = LOCATIONS.get(i.get('location_id'), f"ID:{i.get('location_id')}")
            print(i['order_date'],"  +",i['client_phone'],"  ",i['prod_year'],'year   ',i['engine_volume'],'ccm   ',int(i['price_usd']),'$   ',location_name, i['car_model'],)
            pic='https://static.my.ge/myauto/photos/{}/thumbs/{}_1.jpg'          
            pic1=pic.format(i['photo'],i['car_id'])           
            print(pic1)           
            print(" ")          
            try:
                if yt:
                    print(yt.translate("ka", "ru", i['car_desc']))             
            except:
                pass
            print(" ")
            # Сохраняем полные данные
            make_id = i.get('man_id')  # Правильное поле для марки
            make_name = MAKE_NAMES.get(make_id, f'Unknown-{make_id}') if make_id else 'Unknown'
            model_id = i.get('model_id')  # ID модели
            model_name = MODEL_NAMES.get(model_id, '')  # Название модели из словаря
            trim = i.get('car_model', '')  # Комплектация (Trim)
            
            # Если модель не найдена в словаре, извлекаем первое слово из trim
            if not model_name and trim:
                # car_model обычно содержит: "ModelName Trim Options"
                # Например: "Pathfinder SE 4dr All-wheel Drive" или "Camaro 1LT RS"
                first_word = trim.split()[0] if trim.split() else ''
                # Используем первое слово как название модели
                model_name = first_word
            
            cars_data.append({
                'date': i.get('order_date'),
                'phone': i.get('client_phone'),
                'year': i.get('prod_year'),
                'engine_volume': i.get('engine_volume'),
                'price_usd': int(i.get('price_usd', 0)),
                'location': i.get('location_id'),
                'location_name': LOCATIONS.get(i.get('location_id'), ''),
                'model_id': model_id,  # ID модели (цифра)
                'model': model_name,  # Название модели (из словаря)
                'trim': trim,  # Комплектация/версия
                'photo_url': pic1,
                'description': i.get('car_desc', ''),
                'car_id': i.get('car_id'),
                'make': make_id,  # ID марки авто
                'make_name': make_name,  # Название марки
                'fuel_type': i.get('fuel_type_id'),  # Тип топлива
                'category': i.get('category_id')  # Категория
            })
            
print ("finish!")
print(request)
print(f"Total cars found: {len(cars_data)}")

# Рассчитываем рейтинг для каждого авто (комбо: цена, год, объем)
if cars_data:
    # Найти min/max для нормализации
    prices = [c['price_usd'] for c in cars_data]
    years = [c['year'] for c in cars_data]
    volumes = [c['engine_volume'] for c in cars_data if c['engine_volume'] > 0]
    
    min_price, max_price = min(prices), max(prices)
    min_year, max_year = min(years), max(years)
    min_volume = min(volumes) if volumes else 0
    max_volume = max(volumes) if volumes else 1000
    
    # Добавляем рейтинг к каждому авто
    for car in cars_data:
        # Нормализованные оценки (0-1)
        price_score = 1 - ((car['price_usd'] - min_price) / (max_price - min_price)) if max_price > min_price else 0.5
        year_score = (car['year'] - min_year) / (max_year - min_year) if max_year > min_year else 0.5
        
        if car['engine_volume'] > 0:
            volume_score = (car['engine_volume'] - min_volume) / (max_volume - min_volume) if max_volume > min_volume else 0.5
        else:
            volume_score = 0.3  # Электро/гибриды - меньше балл
        
        # Комбо-рейтинг (средневзвешенный)
        car['rating'] = (price_score * 0.4 + year_score * 0.35 + volume_score * 0.25) * 100
    
    # Сортируем по рейтингу
    top_cars = sorted(cars_data, key=lambda x: x['rating'], reverse=True)[:15]
    
    print("\n" + "="*70)
    print("🏆 ТОП 15 ЛУЧШИХ ВАРИАНТОВ НА РЫНКЕ")
    print("="*70)
    for idx, car in enumerate(top_cars, 1):
        print(f"\n#{idx} | Рейтинг: {car['rating']:.1f}/100")
        print(f"  💰 ${car['price_usd']} | 📅 {car['year']} | ⚙️ {car['engine_volume']} ccm")
        location_display = LOCATIONS.get(car.get('location'), f"ID:{car.get('location')}")
        print(f"  🚗 {car['model']} | 📍 {location_display}")

print("\n" + "="*70)

# ========== ОТСЛЕЖИВАНИЕ ИЗМЕНЕНИЙ И АЛЕРТЫ ==========
print("\n📡 Проверка изменений цен и новых авто...")
new_good_cars, price_drops = find_changes(cars_data, previous_data)

if new_good_cars:
    print(f"\n🆕 Найдено {len(new_good_cars)} новых хороших авто!")
    for car in new_good_cars:
        print(f"  - {car['model']} (${car['price_usd']}, рейтинг {car.get('rating', 0):.1f})")
        # Пытаемся отправить Telegram, если ошибка - логируем в файл
        if not send_new_car_alert(car):
            log_new_car(car)

if price_drops:
    print(f"\n📉 Цены упали на {len(price_drops)} автомобилях!")
    for item in price_drops:
        car = item['car']
        print(f"  - {car['model']}: ${item['old_price']} → ${car['price_usd']} (-{item['drop_percent']:.1f}%)")
        # Пытаемся отправить Telegram, если ошибка - логируем в файл
        if not send_price_drop_alert(car, item['old_price']):
            log_price_drop(car, item['old_price'])

# Сохраняем текущие данные как историю
save_current_data(cars_data)
print("\n✅ История обновлена")

# Отправляем сводку (опционально)
if new_good_cars or price_drops:
    print("\n📊 Отправляем сводку в Telegram...")
    send_summary(len(cars_data), new_good_cars, price_drops, cars_data)
# ====================================================

# Сохраняем в JSON
with open("cars_data.json", "w", encoding='utf-8') as f:
    json.dump(cars_data, f, indent=2, ensure_ascii=False)
    print("Data saved to cars_data.json")

# Сохраняем с красивым форматированием в текстовый файл
# Сортируем по рейтингу
sorted_cars = sorted(cars_data, key=lambda x: x.get('rating', 0), reverse=True)

with open("output11.txt", "w", encoding='utf-8') as f:
    f.write("🏆 ТОП 15 ЛУЧШИХ ВАРИАНТОВ НА РЫНКЕ\n")
    f.write("="*70 + "\n\n")
    
    for idx, car in enumerate(sorted_cars[:15], 1):
        f.write(f"#{idx} | Рейтинг: {car.get('rating', 0):.1f}/100\n")
        f.write(f"Цена: ${car['price_usd']} | Год: {car['year']} | Объем: {car['engine_volume']} ccm\n")
        location_display = LOCATIONS.get(car.get('location'), car.get('location', 'N/A'))
        f.write(f"Модель: {car['model']} | Локация: {location_display}\n")
        f.write("-"*70 + "\n\n")
    
    f.write("\n" + "="*70 + "\nВСЕ АВТОМОБИЛИ (отсортировано по рейтингу)\n" + "="*70 + "\n\n")
    
    for idx, car in enumerate(sorted_cars, 1):
        f.write(f"\n{'='*70}\n")
        f.write(f"#{idx} | Рейтинг: {car.get('rating', 0):.1f}/100\n")
        f.write(f"{'='*70}\n")
        f.write(f"Дата: {car['date']}\n")
        f.write(f"Телефон: {car['phone']}\n")
        f.write(f"Модель: {car['model']}\n")
        f.write(f"Год выпуска: {car['year']}\n")
        f.write(f"Объем двигателя: {car['engine_volume']} ccm\n")
        f.write(f"Цена: ${car['price_usd']}\n")
        location_display = LOCATIONS.get(car.get('location'), car.get('location', 'N/A'))
        f.write(f"Локация: {location_display}\n")
        f.write(f"Фото: {car['photo_url']}\n")
        f.write(f"ID: {car['car_id']}\n")
        f.write(f"Описание: {car['description']}\n")
    
print("Data saved to output11.txt")