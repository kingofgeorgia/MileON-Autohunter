#!/usr/bin/env python3
"""
Скрипт проверки фильтрации автосалонов
Проверяет, что все компоненты системы правильно исключают автосалоны.
"""

import sqlite3
from datetime import datetime

print("=" * 60)
print("ПРОВЕРКА СИСТЕМЫ ФИЛЬТРАЦИИ АВТОСАЛОНОВ")
print("=" * 60)

conn = sqlite3.connect('mileon_saas.db')
cursor = conn.cursor()

# 1. Проверка car_listings
print("\n1️⃣ Проверка таблицы car_listings")
print("-" * 60)

cursor.execute("SELECT COUNT(*) FROM car_listings")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM car_listings WHERE dealer_user_id = 0 OR dealer_user_id IS NULL")
private = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM car_listings WHERE dealer_user_id > 0")
autosalons = cursor.fetchone()[0]

print(f"Всего листингов: {total:,}")
print(f"Частных продавцов: {private:,} ({private/total*100:.1f}%)")
print(f"Автосалонов: {autosalons:,} ({autosalons/total*100:.1f}% if total > 0 else 0)")

if autosalons > 0:
    print("❌ ВНИМАНИЕ: В базе есть автосалоны!")
    cursor.execute("""
        SELECT brand, model, year, price_usd, dealer_user_id 
        FROM car_listings 
        WHERE dealer_user_id > 0 
        LIMIT 5
    """)
    print("\nПримеры автосалонов в базе:")
    for row in cursor.fetchall():
        print(f"  - {row[0]} {row[1]} {row[2]}, ${row[3]:,.0f}, dealer_id={row[4]}")
else:
    print("✅ База данных чистая (автосалоны отсутствуют)")

# 2. Проверка listing_history (если существует)
print("\n2️⃣ Проверка таблицы listing_history")
print("-" * 60)

try:
    cursor.execute("SELECT COUNT(*) FROM listing_history")
    history_count = cursor.fetchone()[0]
    
    if history_count > 0:
        # Проверить, есть ли колонка dealer_user_id
        cursor.execute("PRAGMA table_info(listing_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'dealer_user_id' in columns:
            cursor.execute("SELECT COUNT(*) FROM listing_history WHERE dealer_user_id > 0")
            history_autosalons = cursor.fetchone()[0]
            
            print(f"Всего снимков: {history_count:,}")
            print(f"Автосалонов в истории: {history_autosalons:,}")
            
            if history_autosalons > 0:
                print("❌ В истории есть снимки автосалонов (старые данные)")
            else:
                print("✅ История чистая (автосалоны отсутствуют)")
        else:
            print(f"Всего снимков: {history_count:,}")
            print("⚠️ Колонка dealer_user_id отсутствует (будет добавлена при следующем снимке)")
    else:
        print("ℹ️ История пуста (снимки еще не делались)")
        
except sqlite3.OperationalError:
    print("ℹ️ Таблица listing_history не создана (выполните 'Опция 1' в setup_listing_tracking.py)")

# 3. Проверка estimated_deals
print("\n3️⃣ Проверка таблицы estimated_deals")
print("-" * 60)

try:
    cursor.execute("SELECT COUNT(*) FROM estimated_deals")
    deals_count = cursor.fetchone()[0]
    
    if deals_count > 0:
        # Проверить, сколько сделок связано с автосалонами
        cursor.execute("""
            SELECT COUNT(*)
            FROM estimated_deals ed
            LEFT JOIN car_listings cl ON ed.listing_id = cl.id
            WHERE cl.dealer_user_id > 0
        """)
        autosalon_deals = cursor.fetchone()[0]
        
        print(f"Всего предполагаемых сделок: {deals_count:,}")
        print(f"Сделок от автосалонов: {autosalon_deals:,}")
        
        if autosalon_deals > 0:
            print("❌ ВНИМАНИЕ: Есть сделки от автосалонов (старые данные)")
            print("   Рекомендация: пересоздать estimated_deals (Опция 5 в setup_listing_tracking.py)")
        else:
            print("✅ Все сделки от частных продавцов")
    else:
        print("ℹ️ Предполагаемые сделки не созданы (выполните 'Опция 5' в setup_listing_tracking.py)")
        
except sqlite3.OperationalError:
    print("ℹ️ Таблица estimated_deals не создана")

# 4. Проверка closed_deals
print("\n4️⃣ Проверка таблицы closed_deals")
print("-" * 60)

try:
    cursor.execute("SELECT COUNT(*) FROM closed_deals")
    closed_count = cursor.fetchone()[0]
    
    if closed_count > 0:
        # Проверить автосалоны в closed_deals
        cursor.execute("""
            SELECT COUNT(*)
            FROM closed_deals cd
            LEFT JOIN car_listings cl ON cd.listing_id = cl.id
            WHERE cl.dealer_user_id > 0
        """)
        closed_autosalons = cursor.fetchone()[0]
        
        print(f"Всего закрытых сделок: {closed_count:,}")
        print(f"Сделок от автосалонов: {closed_autosalons:,}")
        
        if closed_autosalons > 0:
            print("⚠️ В closed_deals есть автосалоны (старые данные)")
            print("   Рекомендация: пересоздать через convert_estimated_to_closed.py")
        else:
            print("✅ Все закрытые сделки от частных продавцов")
    else:
        print("ℹ️ Закрытые сделки отсутствуют (выполните convert_estimated_to_closed.py)")
        
except sqlite3.OperationalError:
    print("ℹ️ Таблица closed_deals не создана")

# ИТОГОВАЯ СТАТИСТИКА
print("\n" + "=" * 60)
print("ИТОГОВАЯ СТАТИСТИКА")
print("=" * 60)

issues = []

if autosalons > 0:
    issues.append(f"❌ {autosalons} автосалонов в car_listings")
    
if 'history_autosalons' in locals() and history_autosalons > 0:
    issues.append(f"⚠️ {history_autosalons} автосалонов в listing_history")
    
if 'autosalon_deals' in locals() and autosalon_deals > 0:
    issues.append(f"⚠️ {autosalon_deals} сделок автосалонов в estimated_deals")
    
if 'closed_autosalons' in locals() and closed_autosalons > 0:
    issues.append(f"⚠️ {closed_autosalons} сделок автосалонов в closed_deals")

if issues:
    print("\n🔧 Найдены проблемы:")
    for issue in issues:
        print(f"  {issue}")
    print("\n📋 Рекомендуемые действия:")
    print("  1. Запустить парсер заново (удалит автосалоны из car_listings)")
    print("  2. Создать новые снимки (Опция 2 в setup_listing_tracking.py)")
    print("  3. Пересоздать estimated_deals (Опция 5)")
    print("  4. Пересоздать closed_deals (convert_estimated_to_closed.py)")
else:
    print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    print("   Автосалоны успешно исключены из всех таблиц!")

print("\n" + "=" * 60)
print(f"Проверка завершена: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

conn.close()
