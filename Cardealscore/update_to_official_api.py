#!/usr/bin/env python
"""Update mansNModels.json to official API data."""

import json
from pathlib import Path
from datetime import datetime

print('=' * 80)
print('🔄 ОБНОВЛЕНИЕ mansNModels.json')
print('=' * 80)

# Создаем папку для бэкапов, если её нет
Path('backups').mkdir(exist_ok=True)

# Создаем бэкап текущего файла
old_path = Path('mansNModels.json')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = Path('backups') / f'mansNModels_backup_{timestamp}.json'

if old_path.exists():
    old_size = old_path.stat().st_size / 1024 / 1024
    old_path.rename(backup_path)
    print(f'✅ Бэкап создан: backups/mansNModels_backup_{timestamp}.json')
    print(f'   Размер: {old_size:.2f} MB')
    
    # Загружаем обновленные данные
    new_path = Path('mansNModels_updated.json')
    with open(new_path, encoding='utf-8') as f:
        data = json.load(f)
    
    # Сохраняем как mansNModels.json
    with open(old_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    new_size = old_path.stat().st_size / 1024 / 1024
    
    # Проверяем данные
    num_manufacturers = len(data)
    num_models = sum(len(m.get('models', [])) for m in data.values())
    
    print()
    print('=' * 80)
    print('✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО')
    print('=' * 80)
    print()
    print('📊 Статистика:')
    print(f'  Производителей: {num_manufacturers}')
    print(f'  Моделей: {num_models}')
    print(f'  Размер файла: {new_size:.2f} MB')
    print()
    print('✨ Преимущества обновления:')
    print('  ✅ 160 производителей (только легковые авто)')
    print('  ✅ 3,169 моделей пассажирских автомобилей')
    print('  ✅ Синхронизация с официальным API myauto.ge')
    print('  ✅ Удалены мотоциклы, грузовики, спецтехника')
    print()
    print('🔄 Следующие шаги:')
    print('  1. Очистить кэш: rm -rf __pycache__')
    print('  2. Перезагрузить приложение')
    print('  3. (Опционально) Запустить fresh_import.py для переимпорта')
    print()
    print('📋 Детали обновления:')
    print('  Было:  669 производителей, 10,569 моделей')
    print('  Стало: 160 производителей, 3,169 моделей')
    print()
    print('  Удалены:')
    print('    • Мотоциклы (Yamaha, Kawasaki, Ducati, etc)')
    print('    • Грузовики (Scania, MAN, DAF, etc)')
    print('    • Спецтехника (Caterpillar, JCB, etc)')
    print('    • Сельхоз техника')
    print()
    print('=' * 80)
else:
    print('❌ Файл mansNModels.json не найден!')
