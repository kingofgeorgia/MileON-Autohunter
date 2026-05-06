"""
Настройка системы отслеживания листингов myauto.ge для ML.

Этот скрипт создает инфраструктуру для мониторинга:
1. Таблица listing_history - история состояний каждого листинга
2. Ежедневный сбор снимков данных
3. Определение "проданных" листингов (исчезнувших с сайта)

Использование:
    python setup_listing_tracking.py
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import async_session_maker, init_db
from mileon_saas.models import CarListing


def create_tracking_tables():
    """Создать таблицы для отслеживания истории листингов."""
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    # Таблица для истории снимков листингов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_listing_id TEXT NOT NULL,
            snapshot_date DATE NOT NULL,
            brand TEXT,
            model TEXT,
            year INTEGER,
            price_usd REAL,
            mileage_km INTEGER,
            listing_date TEXT,
            dealer_user_id INTEGER,
            status TEXT DEFAULT 'active',
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_listing_id, snapshot_date)
        )
    """)
    
    # Индексы для быстрого поиска
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_source_id 
        ON listing_history(source_listing_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_date 
        ON listing_history(snapshot_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_status 
        ON listing_history(status)
    """)
    
    # Таблица для предполагаемых сделок (из исчезнувших листингов)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimated_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_listing_id TEXT NOT NULL UNIQUE,
            listing_id INTEGER,
            first_seen DATE,
            last_seen DATE,
            days_listed INTEGER,
            first_price_usd REAL,
            last_price_usd REAL,
            price_change_percent REAL,
            estimated_sell_price REAL,
            confidence_score REAL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(listing_id) REFERENCES car_listings(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Таблицы отслеживания созданы:")
    print("   - listing_history (история снимков)")
    print("   - estimated_deals (предполагаемые сделки)")


async def take_snapshot():
    """
    Сделать снимок текущих листингов.
    Запускайте эту функцию ежедневно (через cron или планировщик).
    """
    await init_db()
    
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    async with async_session_maker() as session:
        # Получить все активные листинги
        result = await session.execute(
            select(CarListing).where(CarListing.source == "myauto")
        )
        listings = result.scalars().all()
        
        added = 0
        updated = 0
        
        for listing in listings:
            if not listing.source_listing_id:
                continue
            
            # Проверить, есть ли уже запись за сегодня
            cursor.execute("""
                SELECT id FROM listing_history 
                WHERE source_listing_id = ? AND snapshot_date = ?
            """, (listing.source_listing_id, today))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновить существующую запись
                cursor.execute("""
                    UPDATE listing_history 
                    SET price_usd = ?, mileage_km = ?, listing_date = ?, status = 'active'
                    WHERE id = ?
                """, (listing.price_usd, listing.mileage_km, listing.listing_date, existing[0]))
                updated += 1
            else:
                # Добавить новую запись
                cursor.execute("""
                    INSERT INTO listing_history 
                    (source_listing_id, snapshot_date, brand, model, year, 
                     price_usd, mileage_km, listing_date, dealer_user_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                """, (
                    listing.source_listing_id,
                    today,
                    listing.brand,
                    listing.model,
                    listing.year,
                    listing.price_usd,
                    listing.mileage_km,
                    listing.listing_date,
                    listing.dealer_user_id,
                ))
                added += 1
        
        conn.commit()
    
    print(f"✅ Снимок за {today}:")
    print(f"   Добавлено: {added}")
    print(f"   Обновлено: {updated}")
    print(f"   Всего активных: {added + updated}")
    
    conn.close()


def mark_disappeared_listings():
    """
    Пометить листинги, которые исчезли (не появились в сегодняшнем снимке).
    """
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Найти листинги, которые были вчера, но нет сегодня
    cursor.execute("""
        SELECT DISTINCT h1.source_listing_id
        FROM listing_history h1
        WHERE h1.snapshot_date = ?
        AND h1.status = 'active'
        AND NOT EXISTS (
            SELECT 1 FROM listing_history h2
            WHERE h2.source_listing_id = h1.source_listing_id
            AND h2.snapshot_date = ?
        )
    """, (yesterday, today))
    
    disappeared = cursor.fetchall()
    
    if not disappeared:
        print("ℹ️ Нет исчезнувших листингов")
        conn.close()
        return
    
    # Пометить как исчезнувшие
    for (source_id,) in disappeared:
        cursor.execute("""
            UPDATE listing_history
            SET status = 'disappeared'
            WHERE source_listing_id = ?
            AND snapshot_date = ?
        """, (source_id, yesterday))
    
    conn.commit()
    
    print(f"🔍 Исчезнувших листингов: {len(disappeared)}")
    
    conn.close()


async def generate_estimated_deals(
    min_days_listed: int = 7,
    max_days_listed: int = 180,
    confidence_threshold: float = 0.5,
):
    """
    Создать предполагаемые сделки из исчезнувших листингов.
    
    Args:
        min_days_listed: Минимум дней в листинге (меньше = подозрительно)
        max_days_listed: Максимум дней (больше = скорее всего сняли, не продали)
        confidence_threshold: Минимальная уверенность для добавления
    """
    await init_db()
    
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    # Найти исчезнувшие листинги с историей
    cursor.execute("""
        SELECT 
            source_listing_id,
            MIN(snapshot_date) as first_seen,
            MAX(snapshot_date) as last_seen,
            MIN(price_usd) as first_price,
            MAX(price_usd) as last_price,
            MAX(listing_date) as original_listing_date
        FROM listing_history
        WHERE status = 'disappeared'
        AND source_listing_id NOT IN (
            SELECT source_listing_id FROM estimated_deals
        )
        GROUP BY source_listing_id
        HAVING COUNT(*) >= ?
    """, (min_days_listed,))
    
    candidates = cursor.fetchall()
    
    if not candidates:
        print("ℹ️ Нет новых кандидатов для предполагаемых сделок")
        conn.close()
        return
    
    print(f"🔍 Найдено кандидатов: {len(candidates)}")
    
    added = 0
    
    for source_id, first_seen, last_seen, first_price, last_price, original_listing_date in candidates:
        # Преобразовать даты
        first_date = datetime.strptime(first_seen, '%Y-%m-%d').date()
        last_date = datetime.strptime(last_seen, '%Y-%m-%d').date()
        days_listed = (last_date - first_date).days
        
        # Вычислить реальное время на myauto.ge (от даты размещения)
        days_on_market = None
        if original_listing_date:
            try:
                # listing_date может быть в формате '2026-02-14 09:56:23'
                listing_dt = datetime.strptime(original_listing_date.split()[0], '%Y-%m-%d').date()
                days_on_market = (last_date - listing_dt).days
            except:
                days_on_market = days_listed
        
        if days_listed > max_days_listed:
            continue  # Слишком долго - скорее всего просто сняли
        
        # Рассчитать уверенность (с учетом автоудаления)
        confidence = calculate_confidence(
            days_listed, 
            first_price, 
            last_price,
            min_days_listed,
            max_days_listed,
            days_on_market,
        )
        
        if confidence < confidence_threshold:
            continue
        
        # Оценить цену продажи (обычно на 5-10% ниже последней листинговой)
        price_change = ((last_price - first_price) / first_price * 100) if first_price else 0
        
        # Если цена снижалась - используем последнюю цену как есть
        # Если цена не менялась - предполагаем продажу на 5% ниже
        if price_change < -5:
            estimated_sell = last_price
            reason = "Цена снижалась, продали по последней цене"
        else:
            estimated_sell = last_price * 0.95
            reason = "Стандартная скидка 5% от листинговой"
        
        # Найти listing_id в основной таблице
        async with async_session_maker() as session:
            listing = await session.scalar(
                select(CarListing).where(
                    CarListing.source_listing_id == source_id
                )
            )
            listing_id = listing.id if listing else None
        
        # Добавить предполагаемую сделку
        cursor.execute("""
            INSERT INTO estimated_deals
            (source_listing_id, listing_id, first_seen, last_seen, days_listed,
             first_price_usd, last_price_usd, price_change_percent,
             estimated_sell_price, confidence_score, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id, listing_id, first_seen, last_seen, days_listed,
            first_price, last_price, price_change,
            estimated_sell, confidence, reason
        ))
        
        added += 1
    
    conn.commit()
    
    print(f"✅ Создано предполагаемых сделок: {added}")
    
    conn.close()


def calculate_confidence(
    days_listed: int,
    first_price: float,
    last_price: float,
    min_days: int,
    max_days: int,
    days_on_market: int = None,
) -> float:
    """
    Рассчитать уверенность в том, что листинг был продан.
    
    Факторы:
    - Оптимальное время в листинге (14-60 дней) = высокая уверенность
    - Снижение цены = высокая уверенность (активно продавали)
    - Слишком быстро (<7 дней) = низкая уверенность (подозрительно)
    - Слишком долго (>180 дней) = низкая уверенность (сняли)
    - АВТОУДАЛЕНИЕ myauto.ge каждые ~30 дней = очень низкая уверенность
    """
    confidence = 0.5  # Базовая уверенность
    
    # Использовать реальное время на рынке, если доступно
    effective_days = days_on_market if days_on_market is not None else days_listed
    
    # КРИТИЧЕСКИЙ ФАКТОР: Автоудаление myauto.ge каждые 30 дней
    # Если листинг исчез ровно через ~30, ~60, ~90 дней - это автоудаление!
    auto_delete_periods = [30, 60, 90, 120, 150, 180]  # Месяцы
    tolerance = 3  # ±3 дня допуск
    
    for period in auto_delete_periods:
        if abs(effective_days - period) <= tolerance:
            # Вероятно автоудаление системой
            confidence -= 0.5  # Сильное снижение уверенности
            break
    
    # Фактор 1: Время в листинге
    if 14 <= effective_days <= 60:
        confidence += 0.3  # Оптимальное время
    elif 7 <= effective_days <= 90:
        confidence += 0.2  # Приемлемое время
    elif effective_days < 7:
        confidence -= 0.2  # Слишком быстро
    elif effective_days > 120:
        confidence -= 0.3  # Слишком долго
    
    # Фактор 2: Изменение цены
    if last_price and first_price:
        price_change_pct = (last_price - first_price) / first_price * 100
        
        if -15 < price_change_pct < -5:
            confidence += 0.2  # Разумное снижение цены
        elif price_change_pct <= -15:
            confidence += 0.1  # Сильное снижение (возможно, проблемы)
        elif price_change_pct > 5:
            confidence -= 0.1  # Цена выросла (странно)
    
    return max(0.0, min(1.0, confidence))


async def stats_estimated_deals():
    """Показать статистику по предполагаемым сделкам."""
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM estimated_deals")
    total = cursor.fetchone()[0]
    
    if total == 0:
        print("❌ Нет предполагаемых сделок")
        conn.close()
        return
    
    print("=" * 60)
    print("  СТАТИСТИКА ПРЕДПОЛАГАЕМЫХ СДЕЛОК")
    print("=" * 60)
    print()
    print(f"📊 Всего сделок: {total}")
    
    # Средняя уверенность
    cursor.execute("SELECT AVG(confidence_score) FROM estimated_deals")
    avg_conf = cursor.fetchone()[0]
    print(f"📈 Средняя уверенность: {avg_conf:.2%}")
    
    # Средние дни
    cursor.execute("SELECT AVG(days_listed) FROM estimated_deals")
    avg_days = cursor.fetchone()[0]
    print(f"⏱️  Средние дни в листинге: {avg_days:.0f}")
    
    # Средняя цена
    cursor.execute("SELECT AVG(estimated_sell_price) FROM estimated_deals")
    avg_price = cursor.fetchone()[0]
    print(f"💰 Средняя предполагаемая цена: ${avg_price:,.0f}")
    
    # По уверенности
    cursor.execute("""
        SELECT 
            CASE 
                WHEN confidence_score >= 0.8 THEN 'Высокая (≥80%)'
                WHEN confidence_score >= 0.6 THEN 'Средняя (60-80%)'
                ELSE 'Низкая (<60%)'
            END as conf_level,
            COUNT(*) as cnt
        FROM estimated_deals
        GROUP BY conf_level
    """)
    
    print()
    print("📊 Распределение по уверенности:")
    for level, cnt in cursor.fetchall():
        print(f"   {level}: {cnt}")
    
    # Примеры
    cursor.execute("""
        SELECT 
            ed.source_listing_id,
            ed.days_listed,
            ed.last_price_usd,
            ed.estimated_sell_price,
            ed.confidence_score,
            cl.brand,
            cl.model,
            cl.year
        FROM estimated_deals ed
        LEFT JOIN car_listings cl ON ed.listing_id = cl.id
        ORDER BY ed.confidence_score DESC
        LIMIT 5
    """)
    
    print()
    print("🔝 ТОП-5 с высокой уверенностью:")
    for row in cursor.fetchall():
        source_id, days, last_price, est_price, conf, brand, model, year = row
        print(f"   {brand or 'N/A'} {model or 'N/A'} {year or 'N/A'}")
        print(f"     Дней: {days} | Листинг: ${last_price:,.0f} → Продажа: ${est_price:,.0f}")
        print(f"     Уверенность: {conf:.0%}")
    
    conn.close()


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

async def main():
    """Интерактивное меню."""
    print("=" * 60)
    print("  СИСТЕМА ОТСЛЕЖИВАНИЯ ЛИСТИНГОВ MYAUTO.GE")
    print("=" * 60)
    print()
    print("Выберите действие:")
    print("  1. Создать таблицы отслеживания (первый запуск)")
    print("  2. Сделать снимок текущих листингов (запускать ежедневно)")
    print("  3. Пометить исчезнувшие листинги")
    print("  4. Создать предполагаемые сделки")
    print("  5. Показать статистику")
    print()
    
    choice = input("Ваш выбор (1-5): ").strip()
    
    if choice == "1":
        create_tracking_tables()
    elif choice == "2":
        await take_snapshot()
    elif choice == "3":
        mark_disappeared_listings()
    elif choice == "4":
        await generate_estimated_deals()
    elif choice == "5":
        await stats_estimated_deals()
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
