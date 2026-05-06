#!/usr/bin/env python3
"""
Проверка полей дилеров в API myauto.ge
"""

import cloudscraper
import json

print("=" * 60)
print("ПРОВЕРКА СТРУКТУРЫ API ДЛЯ ИДЕНТИФИКАЦИИ ДИЛЕРОВ")
print("=" * 60)

# Создать scraper для обхода Cloudflare
scraper = cloudscraper.create_scraper()
scraper.headers.update({
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
})

# Получить несколько страниц
all_items = []
for page in range(1, 4):  # 3 страницы = ~60 объявлений
    print(f"\nЗагрузка страницы {page}...")
    response = scraper.get(
        'https://api2.myauto.ge/en/products',
        params={
            'vehicleType': 0,
            'hideDealPrice': 1,
            'bargainType': 0,
            'ForRent': '',
            'Mans': '',
            'PriceFrom': 600,
            'PriceTo': 50000,
            'CurrencyID': 1,
            'MileageType': 1,
            'Customs': 1,
            'Page': page
        },
        timeout=15
    )
    
    data = response.json()
    items = data.get('data', {}).get('items', [])
    all_items.extend(items)
    print(f"  Получено: {len(items)} объявлений")

print(f"\nВсего получено: {len(all_items)} объявлений\n")

# Проверить известные автомобили
print("=" * 60)
print("ПОИСК АВТОМОБИЛЕЙ 120528452 и 120543779")
print("=" * 60)

target_ids = ['120528452', '120543779']

for car_id in target_ids:
    car = next((i for i in all_items if str(i.get('car_id')) == car_id), None)
    if car:
        print(f"\n✅ НАЙДЕН автомобиль {car_id}:")
        print(f"   user_id: {car.get('user_id')}")
        print(f"   dealer_user_id: {car.get('dealer_user_id')}")
        
        # Проверить все возможные поля дилера
        dealer_fields = ['dealerId', 'dealer_id', 'seller_type', 'is_dealer', 'dealer']
        for field in dealer_fields:
            if field in car:
                print(f"   {field}: {car.get(field)}")
        
        print(f"   Марка: {car.get('man_id')} - Модель: {car.get('model_id')}")
        print(f"   Цена: {car.get('price_usd', car.get('price', 'N/A'))}")
        
        # Показать ВСЕ ключи
        print(f"\n   Все ключи в объекте:")
        for key in sorted(car.keys()):
            value = car.get(key)
            if not isinstance(value, (list, dict)):  # Не выводить сложные объекты
                print(f"     - {key}: {value}")
    else:
        print(f"\n❌ Автомобиль {car_id} НЕ НАЙДЕН в первых {len(all_items)} объявлениях")

# Статистика по dealer_user_id
print("\n" + "=" * 60)
print("СТАТИСТИКА ПО DEALER_USER_ID:")
print("=" * 60)

dealer_counts = {}
for item in all_items:
    dealer_id = item.get('dealer_user_id')
    if dealer_id not in dealer_counts:
        dealer_counts[dealer_id] = 0
    dealer_counts[dealer_id] += 1

private_count = dealer_counts.get(0, 0) + dealer_counts.get(None, 0)
print(f"\ndealer_user_id = 0 или None: {private_count} объявлений ({private_count/len(all_items)*100:.1f}%)")

print(f"\nДилеры (dealer_user_id > 0):")
for dealer_id, count in sorted(dealer_counts.items(), key=lambda x: x[1], reverse=True):
    if dealer_id and dealer_id > 0:
        print(f"  dealer_user_id = {dealer_id}: {count} объявлений")

print("\n" + "=" * 60)
