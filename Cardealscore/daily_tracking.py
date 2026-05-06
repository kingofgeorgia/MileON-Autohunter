"""
Ежедневная задача мониторинга myauto.ge для ML модели.

Запускайте этот скрипт каждый день для:
1. Обновления листингов из API
2. Создания снимка текущих данных
3. Анализа исчезнувших листингов

Автоматизация:
    Windows Task Scheduler:
    - Программа: C:\Users\kingofgeorgia\Documents\GitHub\Cardealscore\.venv\Scripts\python.exe
    - Аргументы: C:\Users\kingofgeorgia\Documents\GitHub\Cardealscore\daily_tracking.py
    - Расписание: Ежедневно в 02:00

Вручную:
    python daily_tracking.py
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from setup_listing_tracking import take_snapshot, mark_disappeared_listings
from mileon_saas.services.ingestion import fetch_and_ingest_myauto


async def daily_run(verbose: bool = True):
    """
    Ежедневная задача мониторинга.
    
    Args:
        verbose: Выводить подробные логи
    """
    start_time = datetime.now()
    
    if verbose:
        print("=" * 60)
        print(f"  ЕЖЕДНЕВНЫЙ МОНИТОРИНГ MYAUTO.GE")
        print("=" * 60)
        print(f"Начало: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    try:
        # Шаг 1: Обновить листинги из API
        if verbose:
            print("📥 [1/3] Загрузка новых листингов из myauto.ge...")
        
        stats = await fetch_and_ingest_myauto(
            limit=100,  # Загрузить до 100 страниц (100 * 20 = 2000 листингов)
            skip_existing=False,  # Обновить существующие
        )
        
        if verbose:
            print(f"   ✅ Обработано: {stats.get('processed', 0)} листингов")
            print(f"   ➕ Добавлено: {stats.get('added', 0)}")
            print(f"   🔄 Обновлено: {stats.get('updated', 0)}")
            print()
        
        # Шаг 2: Сделать снимок текущего состояния
        if verbose:
            print("📸 [2/3] Создание снимка текущих листингов...")
        
        await take_snapshot()
        
        if verbose:
            print()
        
        # Шаг 3: Пометить исчезнувшие листинги
        if verbose:
            print("🔍 [3/3] Анализ исчезнувших листингов...")
        
        mark_disappeared_listings()
        
        # Итоги
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if verbose:
            print()
            print("=" * 60)
            print(f"✅ Мониторинг завершен успешно")
            print(f"Длительность: {duration:.1f} сек")
            print(f"Завершено: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
        
        return True
        
    except Exception as e:
        if verbose:
            print()
            print("=" * 60)
            print(f"❌ ОШИБКА: {e}")
            print("=" * 60)
        
        # Логирование ошибки
        log_error(e)
        
        return False


def log_error(error: Exception):
    """Записать ошибку в лог файл."""
    log_file = Path(__file__).parent / "tracking_errors.log"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {type(error).__name__}: {error}\n")


async def weekly_report():
    """
    Еженедельный отчет (опционально).
    Запускайте каждый понедельник после daily_run().
    """
    import sqlite3
    from datetime import timedelta
    
    conn = sqlite3.connect('mileon_saas.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Статистика за неделю
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT source_listing_id) as total_listings,
            COUNT(DISTINCT CASE WHEN status = 'disappeared' THEN source_listing_id END) as disappeared,
            AVG(price_usd) as avg_price
        FROM listing_history
        WHERE snapshot_date >= ?
    """, (week_ago,))
    
    total, disappeared, avg_price = cursor.fetchone()
    
    print()
    print("=" * 60)
    print(f"  ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ ({week_ago} — {today})")
    print("=" * 60)
    print(f"📊 Всего уникальных листингов: {total}")
    print(f"🔴 Исчезло: {disappeared} ({disappeared/total*100:.1f}%)")
    print(f"💰 Средняя цена: ${avg_price:,.0f}")
    
    # Топ марки
    cursor.execute("""
        SELECT brand, COUNT(*) as cnt
        FROM listing_history
        WHERE snapshot_date >= ? AND status = 'disappeared'
        GROUP BY brand
        ORDER BY cnt DESC
        LIMIT 5
    """, (week_ago,))
    
    print()
    print("🔝 Топ-5 марок (исчезнувших):")
    for brand, cnt in cursor.fetchall():
        print(f"   {brand}: {cnt}")
    
    print("=" * 60)
    
    conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ежедневный мониторинг myauto.ge")
    parser.add_argument('--quiet', '-q', action='store_true', help="Тихий режим (без вывода)")
    parser.add_argument('--weekly', '-w', action='store_true', help="Показать еженедельный отчет")
    
    args = parser.parse_args()
    
    # Основная задача
    success = asyncio.run(daily_run(verbose=not args.quiet))
    
    # Еженедельный отчет (опционально)
    if args.weekly:
        asyncio.run(weekly_report())
    
    # Код возврата для Task Scheduler
    sys.exit(0 if success else 1)
