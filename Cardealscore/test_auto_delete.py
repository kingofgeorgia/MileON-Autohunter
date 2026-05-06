"""
Тест обновленной системы уверенности с учетом автоудаления myauto.ge.
"""

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
    
    is_auto_delete = False
    for period in auto_delete_periods:
        if abs(effective_days - period) <= tolerance:
            # Вероятно автоудаление системой
            confidence -= 0.5  # Сильное снижение уверенности
            is_auto_delete = True
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
    
    return max(0.0, min(1.0, confidence)), is_auto_delete


# ============================================================
# ТЕСТЫ
# ============================================================

print("=" * 70)
print("  ТЕСТЫ СИСТЕМЫ УВЕРЕННОСТИ (С УЧЕТОМ АВТОУДАЛЕНИЯ)")
print("=" * 70)
print()

# Тест 1: Автоудаление 30 дней
print("📋 Тест 1: Листинг исчез ровно через 30 дней")
print("   Описание: Toyota Camry, цена снизилась с $12,000 до $11,400")
conf, is_auto = calculate_confidence(30, 12000, 11400, 7, 180, 30)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'Использовать'}")
print()

# Тест 2: Реальная продажа 42 дня
print("📋 Тест 2: Листинг исчез через 42 дня")
print("   Описание: BMW 3 Series, цена снизилась с $18,000 до $17,100")
conf, is_auto = calculate_confidence(42, 18000, 17100, 7, 180, 42)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ ✅'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'ИСПОЛЬЗОВАТЬ для ML ✅'}")
print()

# Тест 3: Автоудаление 60 дней
print("📋 Тест 3: Листинг исчез ровно через 61 день")
print("   Описание: Mercedes E-Class, цена снизилась с $25,000 до $23,500")
conf, is_auto = calculate_confidence(61, 25000, 23500, 7, 180, 61)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'Использовать'}")
print()

# Тест 4: Быстрая продажа 18 дней
print("📋 Тест 4: Листинг исчез через 18 дней")
print("   Описание: Honda Civic, цена снизилась с $10,000 до $9,500")
conf, is_auto = calculate_confidence(18, 10000, 9500, 7, 180, 18)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ ✅'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'ИСПОЛЬЗОВАТЬ для ML ✅'}")
print()

# Тест 5: Долгий листинг 95 дней (не автоудаление)
print("📋 Тест 5: Листинг исчез через 95 дней")
print("   Описание: Lexus RX, цена без изменений $35,000")
conf, is_auto = calculate_confidence(95, 35000, 35000, 7, 180, 95)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ ✅'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'Использовать'}")
print()

# Тест 6: Автоудаление 90 дней
print("📋 Тест 6: Листинг исчез ровно через 90 дней")
print("   Описание: Audi A4, цена немного снизилась с $22,000 до $21,500")
conf, is_auto = calculate_confidence(90, 22000, 21500, 7, 180, 90)
print(f"   Результат: {conf:.0%} уверенности")
print(f"   Автоудаление: {'ДА ⚠️' if is_auto else 'НЕТ'}")
print(f"   Вывод: {'ИСКЛЮЧИТЬ из обучения' if conf < 0.5 else 'Использовать'}")
print()

# Статистика
print("=" * 70)
print("📊 ИТОГОВАЯ СТАТИСТИКА:")
print("=" * 70)

tests = [
    ("30 дней (автоудаление)", 30, 12000, 11400),
    ("42 дня (реальная продажа)", 42, 18000, 17100),
    ("61 день (автоудаление)", 61, 25000, 23500),
    ("18 дней (быстрая продажа)", 18, 10000, 9500),
    ("95 дней (долгий)", 95, 35000, 35000),
    ("90 дней (автоудаление)", 90, 22000, 21500),
]

passed = 0
total = len(tests)

for name, days, first_price, last_price in tests:
    conf, is_auto = calculate_confidence(days, first_price, last_price, 7, 180, days)
    
    # Ожидаемые результаты
    should_be_auto = days in [30, 60, 90]
    should_pass = conf >= 0.6  # Порог для использования в ML
    
    status = "✅" if is_auto == should_be_auto else "❌"
    print(f"{status} {name}: {conf:.0%} уверенности, автоудаление={is_auto}")
    
    if conf >= 0.6:
        passed += 1

print()
print(f"Годных для ML: {passed}/{total} ({passed/total*100:.0f}%)")
print()

# Рекомендации
print("💡 РЕКОМЕНДАЦИИ:")
print("   - Минимальная уверенность: 60-70% (фильтрует автоудаления)")
print("   - Ожидаемое качество модели с фильтрацией: R² 0.70-0.75")
print("   - Ожидаемое качество БЕЗ фильтрации: R² 0.55-0.60")
print()
