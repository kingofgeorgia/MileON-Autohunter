"""
Преобразование предполагаемых сделок в закрытые сделки для ML.

Этот скрипт берет данные из estimated_deals и создает записи в closed_deals,
которые можно использовать для обучения ML модели.

⚠️ ВАЖНО: Это ПРЕДПОЛАГАЕМЫЕ сделки, не реальные!
   Модель будет менее точной, чем на реальных данных.

Использование:
    python convert_estimated_to_closed.py
"""
import asyncio
import sqlite3
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import async_session_maker, init_db
from mileon_saas.models import CarListing, ClosedDeal


async def convert_estimated_deals(
    min_confidence: float = 0.6,
    discount_factor: float = 0.95,
    default_repair_cost: float = 500.0,
    company_id: int = 1,
) -> int:
    """
    Преобразовать предполагаемые сделки в закрытые.
    
    Args:
        min_confidence: Минимальная уверенность для конвертации
        discount_factor: Множитель для оценки цены покупки от листинговой
        default_repair_cost: Предполагаемая стоимость ремонта
        company_id: ID компании
    
    Returns:
        int: Количество созданных сделок
    """
    await init_db()
    
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    # Получить предполагаемые сделки с достаточной уверенностью
    cursor.execute("""
        SELECT 
            ed.id,
            ed.source_listing_id,
            ed.listing_id,
            ed.days_listed,
            ed.first_price_usd,
            ed.last_price_usd,
            ed.estimated_sell_price,
            ed.confidence_score,
            cl.brand,
            cl.model,
            cl.year
        FROM estimated_deals ed
        LEFT JOIN car_listings cl ON ed.listing_id = cl.id
        WHERE ed.confidence_score >= ?
        AND ed.listing_id IS NOT NULL
        AND ed.listing_id NOT IN (
            SELECT listing_id FROM closed_deals
        )
        ORDER BY ed.confidence_score DESC
    """, (min_confidence,))
    
    candidates = cursor.fetchall()
    
    if not candidates:
        print(f"❌ Нет сделок с уверенностью >= {min_confidence:.0%}")
        conn.close()
        return 0
    
    print(f"🔍 Найдено кандидатов: {len(candidates)}")
    print(f"   Минимальная уверенность: {min_confidence:.0%}")
    print(f"   Предполагаемая цена покупки: {discount_factor:.0%} от листинговой")
    print(f"   Предполагаемый ремонт: ${default_repair_cost:,.0f}")
    print()
    
    print("📋 ПРИМЕРЫ СДЕЛОК:")
    print("-" * 80)
    
    for i, row in enumerate(candidates[:5], 1):
        (est_id, source_id, listing_id, days, first_price, last_price, 
         sell_price, confidence, brand, model, year) = row
        
        purchase_price = first_price * discount_factor
        net_profit = sell_price - purchase_price - default_repair_cost
        roi = (net_profit / purchase_price * 100) if purchase_price > 0 else 0
        
        print(f"{i}. {brand} {model} {year}")
        print(f"   Купили: ${purchase_price:,.0f} → Продали: ${sell_price:,.0f}")
        print(f"   Прибыль: ${net_profit:,.0f} | ROI: {roi:.1f}% | Дней: {days}")
        print(f"   Уверенность: {confidence:.0%}")
    
    if len(candidates) > 5:
        print(f"   ... и ещё {len(candidates) - 5} сделок")
    
    print()
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ:")
    print("   Это ПРЕДПОЛАГАЕМЫЕ сделки на основе исчезнувших листингов.")
    print("   Реальные цены покупки и продажи могут отличаться.")
    print("   ML модель будет менее точной, чем на реальных данных.")
    print()
    
    choice = input(f"Создать {len(candidates)} закрытых сделок? (y/n): ").strip().lower()
    
    if choice != 'y':
        print("❌ Отменено")
        conn.close()
        return 0
    
    # Создать закрытые сделки
    added = 0
    
    async with async_session_maker() as session:
        for row in candidates:
            (est_id, source_id, listing_id, days, first_price, last_price, 
             sell_price, confidence, brand, model, year) = row
            
            # Оценить цену покупки (обычно на 5% ниже первой листинговой)
            purchase_price = first_price * discount_factor
            
            # Оценить ремонт на основе разницы цен
            if last_price < first_price:
                # Если цена снижалась - возможно, были проблемы
                repair_cost = default_repair_cost * 1.5
            else:
                repair_cost = default_repair_cost
            
            # Рассчитать прибыль и ROI
            net_profit = sell_price - purchase_price - repair_cost
            roi_percent = (net_profit / purchase_price * 100) if purchase_price > 0 else 0.0
            
            # Создать сделку
            deal = ClosedDeal(
                company_id=company_id,
                listing_id=listing_id,
                purchase_price=purchase_price,
                sell_price=sell_price,
                days_held=days,
                repair_cost=repair_cost,
                net_profit=net_profit,
                roi_percent=roi_percent,
            )
            
            session.add(deal)
            added += 1
        
        await session.commit()
    
    print()
    print(f"✅ Создано закрытых сделок: {added}")
    
    # Статистика
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(net_profit) as avg_profit,
            AVG(roi_percent) as avg_roi,
            AVG(days_held) as avg_days
        FROM closed_deals
    """)
    
    total, avg_profit, avg_roi, avg_days = cursor.fetchone()
    
    print()
    print("📊 ОБЩАЯ СТАТИСТИКА CLOSED_DEALS:")
    print(f"   Всего сделок: {total}")
    print(f"   Средняя прибыль: ${avg_profit:,.0f}")
    print(f"   Средний ROI: {avg_roi:.1f}%")
    print(f"   Средние дни: {avg_days:.0f}")
    
    conn.close()
    
    return added


async def clear_estimated_deals():
    """Удалить все предполагаемые сделки (для повторного запуска)."""
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM estimated_deals")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("ℹ️ Таблица estimated_deals пустая")
        conn.close()
        return
    
    print(f"⚠️ Будет удалено {count} предполагаемых сделок")
    choice = input("Продолжить? (y/n): ").strip().lower()
    
    if choice == 'y':
        cursor.execute("DELETE FROM estimated_deals")
        conn.commit()
        print(f"✅ Удалено: {count}")
    else:
        print("❌ Отменено")
    
    conn.close()


async def clear_closed_deals():
    """Удалить закрытые сделки (ОПАСНО! Только для тестирования)."""
    await init_db()
    
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM closed_deals")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("ℹ️ Таблица closed_deals пустая")
        conn.close()
        return
    
    print()
    print("🚨 ОПАСНО! 🚨")
    print(f"   Будет удалено {count} закрытых сделок")
    print("   Это необратимая операция!")
    print()
    
    choice = input("Вы уверены? Введите 'DELETE' для подтверждения: ").strip()
    
    if choice == 'DELETE':
        cursor.execute("DELETE FROM closed_deals")
        conn.commit()
        print(f"✅ Удалено: {count}")
    else:
        print("❌ Отменено")
    
    conn.close()


async def main():
    """Интерактивное меню."""
    print("=" * 60)
    print("  ПРЕОБРАЗОВАНИЕ ПРЕДПОЛАГАЕМЫХ СДЕЛОК В ЗАКРЫТЫЕ")
    print("=" * 60)
    print()
    print("Выберите действие:")
    print("  1. Преобразовать estimated_deals → closed_deals")
    print("  2. Очистить estimated_deals (для повторного запуска)")
    print("  3. Очистить closed_deals (ОПАСНО!)")
    print()
    
    choice = input("Ваш выбор (1-3): ").strip()
    
    if choice == "1":
        min_conf = float(input("Минимальная уверенность (0.6): ").strip() or "0.6")
        await convert_estimated_deals(min_confidence=min_conf)
    elif choice == "2":
        await clear_estimated_deals()
    elif choice == "3":
        await clear_closed_deals()
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
