"""Проверка количества закрытых сделок в базе данных."""
import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('mileon_saas.db')
cursor = conn.cursor()

# Количество закрытых сделок
cursor.execute("SELECT COUNT(*) FROM closed_deals")
total_deals = cursor.fetchone()[0]
print(f"📊 Всего закрытых сделок: {total_deals}")

if total_deals > 0:
    # Пример данных из closed_deals
    cursor.execute("""
        SELECT 
            cd.id,
            cd.purchase_price,
            cd.sell_price,
            cd.days_held,
            cd.repair_cost,
            cd.net_profit,
            cd.roi_percent,
            cl.brand,
            cl.model,
            cl.year
        FROM closed_deals cd
        JOIN car_listings cl ON cd.listing_id = cl.id
        LIMIT 5
    """)
    
    print("\n🔍 Примеры закрытых сделок:")
    print("-" * 80)
    for row in cursor.fetchall():
        deal_id, purchase, sell, days, repair, profit, roi, brand, model, year = row
        print(f"#{deal_id}: {brand} {model} {year}")
        print(f"  Купили: ${purchase:,.0f} → Продали: ${sell:,.0f}")
        print(f"  Прибыль: ${profit:,.0f} | ROI: {roi:.1f}% | Держали: {days} дней")
        print()
else:
    print("\n⚠️ В базе нет закрытых сделок!")
    print("Для обучения ML модели нужно добавить данные о продажах.")

conn.close()
