"""
Скрипт для добавления закрытых сделок в базу данных.

Закрытые сделки нужны для обучения ML модели прогнозирования цен продажи.

Использование:
1. Вручную через функцию add_deal()
2. Массово из CSV файла через import_from_csv()
"""
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import async_session_maker, init_db
from mileon_saas.models import CarListing, ClosedDeal


async def add_deal(
    session: AsyncSession,
    listing_id: int,
    purchase_price: float,
    sell_price: float,
    days_held: int,
    repair_cost: float = 0.0,
    company_id: int = 1,
) -> ClosedDeal:
    """
    Добавить закрытую сделку.
    
    Args:
        listing_id: ID листинга из car_listings
        purchase_price: Цена покупки (USD)
        sell_price: Цена продажи (USD)
        days_held: Сколько дней держали авто
        repair_cost: Стоимость ремонта (USD)
        company_id: ID компании
    
    Returns:
        ClosedDeal: Созданная сделка
    """
    # Проверить, что листинг существует
    listing = await session.scalar(select(CarListing).where(CarListing.id == listing_id))
    if not listing:
        raise ValueError(f"Листинг #{listing_id} не найден в базе!")
    
    # Рассчитать прибыль и ROI
    net_profit = sell_price - purchase_price - repair_cost
    roi_percent = (net_profit / purchase_price * 100) if purchase_price > 0 else 0.0
    
    # Создать сделку
    deal = ClosedDeal(
        company_id=company_id,
        listing_id=listing_id,
        purchase_price=purchase_price,
        sell_price=sell_price,
        days_held=days_held,
        repair_cost=repair_cost,
        net_profit=net_profit,
        roi_percent=roi_percent,
    )
    
    session.add(deal)
    await session.commit()
    await session.refresh(deal)
    
    print(f"✅ Сделка #{deal.id} добавлена:")
    print(f"   {listing.brand} {listing.model} {listing.year}")
    print(f"   Купили: ${purchase_price:,.0f} → Продали: ${sell_price:,.0f}")
    print(f"   Прибыль: ${net_profit:,.0f} | ROI: {roi_percent:.1f}% | Держали: {days_held} дней")
    
    return deal


async def import_from_csv(csv_path: str, company_id: int = 1) -> int:
    """
    Импорт закрытых сделок из CSV файла.
    
    Формат CSV (с заголовками):
    listing_id,purchase_price,sell_price,days_held,repair_cost
    
    Пример:
    1,10000,12500,45,500
    2,8500,9800,30,200
    
    Args:
        csv_path: Путь к CSV файлу
        company_id: ID компании
    
    Returns:
        int: Количество импортированных сделок
    """
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"Файл {csv_path} не найден!")
    
    count = 0
    async with async_session_maker() as session:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    await add_deal(
                        session=session,
                        listing_id=int(row['listing_id']),
                        purchase_price=float(row['purchase_price']),
                        sell_price=float(row['sell_price']),
                        days_held=int(row['days_held']),
                        repair_cost=float(row.get('repair_cost', 0.0)),
                        company_id=company_id,
                    )
                    count += 1
                except Exception as e:
                    print(f"❌ Ошибка в строке {count + 1}: {e}")
                    continue
    
    print(f"\n📊 Импортировано сделок: {count}")
    return count


async def find_listing_by_car(
    session: AsyncSession,
    brand: str,
    model: str,
    year: int,
    company_id: int = 1,
) -> list[CarListing]:
    """
    Найти листинги по марке/модели/году для получения listing_id.
    
    Используйте эту функцию, если не знаете listing_id.
    """
    result = await session.scalars(
        select(CarListing).where(
            CarListing.company_id == company_id,
            CarListing.brand.ilike(f"%{brand}%"),
            CarListing.model.ilike(f"%{model}%"),
            CarListing.year == year,
        )
    )
    listings = result.all()
    
    if listings:
        print(f"\n🔍 Найдено листингов: {len(listings)}")
        for listing in listings[:10]:  # Показать первые 10
            print(f"   ID: {listing.id} | {listing.brand} {listing.model} {listing.year} | ${listing.price_usd:,.0f}")
    else:
        print(f"⚠️ Листинги не найдены: {brand} {model} {year}")
    
    return listings


# ============================================================
#  ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================

async def example_add_single_deal():
    """Пример: добавить одну сделку вручную."""
    await init_db()
    
    async with async_session_maker() as session:
        # 1. Найти listing_id нужного автомобиля
        listings = await find_listing_by_car(
            session=session,
            brand="Toyota",
            model="Camry",
            year=2018,
        )
        
        if not listings:
            print("❌ Сначала добавьте листинги в базу (через GUI или парсер)")
            return
        
        # 2. Добавить закрытую сделку
        listing_id = listings[0].id
        await add_deal(
            session=session,
            listing_id=listing_id,
            purchase_price=12000,  # Купили за $12,000
            sell_price=14500,      # Продали за $14,500
            days_held=35,          # Держали 35 дней
            repair_cost=300,       # Потратили $300 на ремонт
        )


async def example_import_from_csv():
    """Пример: импорт нескольких сделок из CSV."""
    await init_db()
    
    # Создать пример CSV файла
    csv_content = """listing_id,purchase_price,sell_price,days_held,repair_cost
1,10000,12500,45,500
2,8500,9800,30,200
5,15000,17200,60,800
"""
    
    csv_path = "closed_deals_import.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    print(f"📝 Создан пример CSV файла: {csv_path}")
    print("Отредактируйте его и запустите импорт:\n")
    print(f"  await import_from_csv('{csv_path}')\n")
    
    # Раскомментируйте для импорта:
    # await import_from_csv(csv_path)


async def example_search_and_add():
    """Пример: найти авто и добавить сделку."""
    await init_db()
    
    async with async_session_maker() as session:
        print("🔍 Ищем BMW 3 Series 2015...")
        listings = await find_listing_by_car(
            session=session,
            brand="BMW",
            model="3 Series",
            year=2015,
        )
        
        if listings:
            print(f"\nВыберите listing_id из списка выше и используйте add_deal()")
            print(f"\nПример:")
            print(f"  listing_id = {listings[0].id}")
            print(f"  await add_deal(session, listing_id, purchase_price=20000, sell_price=23000, days_held=40)")


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

async def main():
    """Интерактивное меню для добавления сделок."""
    await init_db()
    
    print("=" * 60)
    print("  ДОБАВЛЕНИЕ ЗАКРЫТЫХ СДЕЛОК ДЛЯ ОБУЧЕНИЯ ML")
    print("=" * 60)
    print("\nВыберите действие:")
    print("  1. Найти листинг по марке/модели/году")
    print("  2. Добавить сделку вручную")
    print("  3. Импортировать из CSV")
    print("  4. Создать пример CSV файла")
    print()
    
    choice = input("Ваш выбор (1-4): ").strip()
    
    async with async_session_maker() as session:
        if choice == "1":
            brand = input("Марка: ").strip()
            model = input("Модель: ").strip()
            year = int(input("Год: ").strip())
            await find_listing_by_car(session, brand, model, year)
        
        elif choice == "2":
            listing_id = int(input("listing_id: ").strip())
            purchase_price = float(input("Цена покупки (USD): ").strip())
            sell_price = float(input("Цена продажи (USD): ").strip())
            days_held = int(input("Дней держали: ").strip())
            repair_cost = float(input("Стоимость ремонта (USD, 0 если нет): ").strip() or 0)
            
            await add_deal(
                session=session,
                listing_id=listing_id,
                purchase_price=purchase_price,
                sell_price=sell_price,
                days_held=days_held,
                repair_cost=repair_cost,
            )
        
        elif choice == "3":
            csv_path = input("Путь к CSV файлу: ").strip()
            await import_from_csv(csv_path)
        
        elif choice == "4":
            csv_path = "closed_deals_template.csv"
            csv_content = """listing_id,purchase_price,sell_price,days_held,repair_cost
1,10000,12500,45,500
2,8500,9800,30,200
"""
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            print(f"✅ Создан шаблон CSV: {csv_path}")
            print("Отредактируйте его и запустите импорт (опция 3)")


if __name__ == "__main__":
    asyncio.run(main())
