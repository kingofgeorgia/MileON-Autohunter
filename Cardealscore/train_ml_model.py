"""
Скрипт для обучения ML модели прогнозирования цен продажи.

Модель обучается на данных закрытых сделок из таблицы closed_deals.

Использование:
    python train_ml_model.py
"""
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import async_session_maker, init_db
from mileon_saas.models import CarListing, ClosedDeal, MarketStats
from mileon_saas.services.common import condition_score, expected_mileage
from mileon_saas.services.ml import train_model, save_model


async def prepare_training_data(session: AsyncSession, company_id: int = 1) -> list[dict]:
    """
    Подготовить данные для обучения из закрытых сделок.
    
    Args:
        session: Сессия базы данных
        company_id: ID компании
    
    Returns:
        list[dict]: Список записей с признаками и целевой переменной (sell_price)
    """
    # Получить все закрытые сделки с полной информацией о листингах
    result = await session.execute(
        select(ClosedDeal, CarListing)
        .join(CarListing, ClosedDeal.listing_id == CarListing.id)
        .where(ClosedDeal.company_id == company_id)
    )
    
    deals_with_listings = result.all()
    
    if not deals_with_listings:
        raise ValueError("❌ В базе нет закрытых сделок для обучения!")
    
    print(f"📊 Найдено закрытых сделок: {len(deals_with_listings)}")
    
    training_records = []
    
    for deal, listing in deals_with_listings:
        # Получить рыночную статистику (если есть)
        market_stats = await session.scalar(
            select(MarketStats).where(
                MarketStats.company_id == company_id,
                MarketStats.brand == listing.brand,
                MarketStats.model == listing.model,
                MarketStats.year == listing.year,
            )
        )
        
        # Рассчитать признаки
        median_price = market_stats.median_price_usd if market_stats else None
        expected = expected_mileage(listing.year)
        
        mileage_deviation = 0.0
        if expected and listing.mileage_km is not None and expected > 0:
            mileage_deviation = (listing.mileage_km - expected) / expected
        
        price_vs_market = 0.0
        if median_price and listing.price_usd:
            price_vs_market = (listing.price_usd - median_price) / median_price
        
        # Добавить запись для обучения
        record = {
            # Категориальные признаки
            "brand": listing.brand or "unknown",
            "model": listing.model or "unknown",
            "engine_type": listing.engine_type or "unknown",
            "transmission": listing.transmission or "unknown",
            "drivetrain": listing.drivetrain or "unknown",
            "imported_from": listing.imported_from or "unknown",
            "accident_history": listing.accident_history or "unknown",
            
            # Числовые признаки
            "year": listing.year or 0,
            "mileage_km": listing.mileage_km or 0,
            "owners_count": listing.owners_count or 0,
            "mileage_deviation": mileage_deviation,
            "price_vs_market": price_vs_market,
            "liquidity_score": 5.0,  # Дефолтное значение (можно улучшить)
            "condition_score": condition_score(listing.accident_history),
            
            # Целевая переменная (то, что предсказываем)
            "sell_price": deal.sell_price,
        }
        
        training_records.append(record)
    
    print(f"✅ Подготовлено записей для обучения: {len(training_records)}")
    return training_records


async def train_and_save_model(company_id: int = 1, min_deals: int = 50) -> None:
    """
    Обучить модель и сохранить на диск.
    
    Args:
        company_id: ID компании
        min_deals: Минимальное количество сделок для обучения
    """
    await init_db()
    
    print("=" * 60)
    print("  ОБУЧЕНИЕ ML МОДЕЛИ ПРОГНОЗИРОВАНИЯ ЦЕН")
    print("=" * 60)
    print()
    
    async with async_session_maker() as session:
        # Подготовить данные
        try:
            training_data = await prepare_training_data(session, company_id)
        except ValueError as e:
            print(str(e))
            print()
            print("💡 Сначала добавьте закрытые сделки:")
            print("   python add_closed_deals.py")
            return
        
        # Проверить минимальное количество
        if len(training_data) < min_deals:
            print(f"⚠️ Недостаточно данных для обучения!")
            print(f"   Есть: {len(training_data)} сделок")
            print(f"   Нужно минимум: {min_deals} сделок")
            print()
            print(f"💡 Рекомендации:")
            print(f"   - Минимум 50-100 сделок для базовой модели")
            print(f"   - 200-500 сделок для хорошего качества")
            print(f"   - 1000+ сделок для высокой точности")
            print()
            
            choice = input(f"Продолжить обучение на {len(training_data)} сделках? (y/n): ").strip().lower()
            if choice != 'y':
                print("❌ Обучение отменено")
                return
        
        # Обучить модель
        print()
        print("🔄 Обучение модели...")
        print("   Алгоритм: GradientBoostingRegressor")
        print("   Разделение: 80% обучение, 20% тест")
        print()
        
        try:
            bundle = train_model(training_data, target_field="sell_price")
        except Exception as e:
            print(f"❌ Ошибка обучения: {e}")
            return
        
        # Показать метрики
        print("✅ Обучение завершено!")
        print()
        print(f"📈 МЕТРИКИ МОДЕЛИ:")
        print(f"   R² Score: {bundle.r2:.4f} ({bundle.r2 * 100:.2f}%)")
        print(f"   Количество признаков: {len(bundle.columns)}")
        print()
        
        # Интерпретация R²
        if bundle.r2 >= 0.85:
            quality = "🟢 Отличная"
            recommendation = "Модель готова к использованию"
        elif bundle.r2 >= 0.75:
            quality = "🟡 Хорошая"
            recommendation = "Модель используется для расчета ROI"
        elif bundle.r2 >= 0.60:
            quality = "🟠 Средняя"
            recommendation = "Модель только для справки (не влияет на ROI)"
        else:
            quality = "🔴 Низкая"
            recommendation = "Добавьте больше данных"
        
        print(f"   Качество: {quality}")
        print(f"   Рекомендация: {recommendation}")
        print()
        
        # Сохранить модель
        print("💾 Сохранение модели...")
        save_model(bundle)
        
        print(f"✅ Модель сохранена:")
        print(f"   - ml_model.joblib (обученная модель)")
        print(f"   - ml_metadata.json (R²={bundle.r2:.4f}, {len(bundle.columns)} признаков)")
        print()
        
        # Инструкции
        print("🎯 ИСПОЛЬЗОВАНИЕ:")
        print("   1. Перезапустите GUI для загрузки новой модели")
        print("   2. Колонка 'ML цена' покажет прогнозы для всех авто")
        
        if bundle.r2 >= 0.75:
            print("   3. ML цена ИСПОЛЬЗУЕТСЯ для расчета ROI и прибыли ✅")
        else:
            print("   3. ML цена НЕ используется (R² < 75%), только отображается")
        
        print()
        print("📊 ПЕРЕОБУЧЕНИЕ:")
        print("   Запускайте обучение каждые 3-6 месяцев или после 100+ новых сделок")


async def show_stats():
    """Показать статистику по закрытым сделкам."""
    await init_db()
    
    async with async_session_maker() as session:
        # Общая статистика
        result = await session.execute(
            select(ClosedDeal).order_by(ClosedDeal.created_at.desc())
        )
        deals = result.scalars().all()
        
        if not deals:
            print("❌ В базе нет закрытых сделок")
            return
        
        print("=" * 60)
        print("  СТАТИСТИКА ЗАКРЫТЫХ СДЕЛОК")
        print("=" * 60)
        print()
        print(f"📊 Всего сделок: {len(deals)}")
        print()
        
        # Средние значения
        avg_roi = sum(d.roi_percent for d in deals) / len(deals)
        avg_profit = sum(d.net_profit for d in deals) / len(deals)
        avg_days = sum(d.days_held for d in deals) / len(deals)
        
        print(f"📈 СРЕДНИЕ ПОКАЗАТЕЛИ:")
        print(f"   ROI: {avg_roi:.1f}%")
        print(f"   Прибыль: ${avg_profit:,.0f}")
        print(f"   Дней держали: {avg_days:.0f}")
        print()
        
        # Последние 5 сделок
        print(f"🕒 ПОСЛЕДНИЕ 5 СДЕЛОК:")
        for deal in deals[:5]:
            listing = await session.scalar(
                select(CarListing).where(CarListing.id == deal.listing_id)
            )
            if listing:
                print(f"   {listing.brand} {listing.model} {listing.year}")
                print(f"     ${deal.purchase_price:,.0f} → ${deal.sell_price:,.0f} | ROI: {deal.roi_percent:.1f}%")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        asyncio.run(show_stats())
    else:
        asyncio.run(train_and_save_model())
