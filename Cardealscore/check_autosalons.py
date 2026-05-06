"""Проверка автосалонов в API данных."""
import json
import sqlite3

# Проверка API ответа
try:
    with open('api_response.json', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('data', {}).get('items', [])
    print(f"📊 Всего листингов в API: {len(items)}")
    
    # Проверка dealer_user_id
    dealers = [i for i in items if i.get('dealer_user_id', 0) > 0]
    print(f"🏢 С dealer_user_id > 0: {len(dealers)}")
    
    if dealers:
        print("\nПример автосалона:")
        example = dealers[0]
        print(f"  car_id: {example.get('car_id')}")
        print(f"  dealer_user_id: {example.get('dealer_user_id')}")
        print(f"  user_id: {example.get('user_id')}")
        print(f"  brand: {example.get('man_id')}")
        print(f"  price: ${example.get('price_usd')}")
    
    # Проверка других полей, которые могут указывать на автосалон
    print("\n🔍 Поиск отличий автосалонов:")
    sample_dealer = dealers[0] if dealers else {}
    sample_private = [i for i in items if i.get('dealer_user_id', 0) == 0][0] if items else {}
    
    print("\nАвтосалон - уникальные ключи:")
    dealer_keys = set(sample_dealer.keys())
    private_keys = set(sample_private.keys())
    unique_dealer = dealer_keys - private_keys
    if unique_dealer:
        print(f"  {unique_dealer}")
    
except FileNotFoundError:
    print("⚠️ api_response.json не найден")

# Проверка базы данных
print("\n" + "="*60)
print("📊 ПРОВЕРКА БАЗЫ ДАННЫХ")
print("="*60)

conn = sqlite3.connect('mileon_saas.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM car_listings")
total = cursor.fetchone()[0]
print(f"Всего листингов: {total}")

cursor.execute("SELECT COUNT(*) FROM car_listings WHERE dealer_user_id IS NOT NULL AND dealer_user_id > 0")
dealers_db = cursor.fetchone()[0]
print(f"С dealer_user_id > 0: {dealers_db}")

if dealers_db > 0:
    cursor.execute("""
        SELECT source_listing_id, brand, model, price_usd, dealer_user_id, user_id
        FROM car_listings 
        WHERE dealer_user_id > 0
        LIMIT 5
    """)
    
    print("\nПримеры автосалонов в БД:")
    for sid, brand, model, price, dealer_id, user_id in cursor.fetchall():
        print(f"  {sid} | {brand} {model} | ${price:,.0f} | dealer={dealer_id}, user={user_id}")

# Проверка по продолжительности листинга
print("\n" + "="*60)
print("📅 ПРОВЕРКА ВРЕМЕНИ НА РЫНКЕ")
print("="*60)

cursor.execute("""
    SELECT 
        source_listing_id,
        brand,
        model,
        listing_date,
        created_at,
        julianday('now') - julianday(listing_date) as days_on_market,
        dealer_user_id
    FROM car_listings
    WHERE listing_date IS NOT NULL
    ORDER BY days_on_market DESC
    LIMIT 10
""")

print("Топ-10 самых долгих листингов:")
for sid, brand, model, listing_date, created_at, days, dealer_id in cursor.fetchall():
    dealer_mark = "🏢" if dealer_id and dealer_id > 0 else "👤"
    print(f"  {dealer_mark} {days:.0f} дней | {brand} {model} | {listing_date}")

conn.close()
