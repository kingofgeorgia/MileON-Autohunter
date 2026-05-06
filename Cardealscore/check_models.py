import json
import sqlite3

# Проверить БД
conn = sqlite3.connect('mileon_saas.db')
cur = conn.cursor()

# Примеры моделей из БД
cur.execute('SELECT brand, model, COUNT(*) as cnt FROM car_listings GROUP BY brand, model ORDER BY cnt DESC LIMIT 25')
results = cur.fetchall()

print("Примеры моделей из БД (первые 25):")
for brand, model, cnt in results:
    print(f"  {brand}: {model} ({cnt} объявлений)")

# Статистика по зависимости brand/model
cur.execute('SELECT COUNT(DISTINCT brand) as makes, COUNT(DISTINCT model) as models FROM car_listings')
makes_cnt, models_cnt = cur.fetchone()
print(f"\nВ БД: {makes_cnt} марок, {models_cnt} моделей")

print("\n" + "="*70)

# Проверить mansNModels.json
with open('mansNModels.json', encoding='utf-8') as f:
    mans = json.load(f)

print(f"В mansNModels.json: {len(mans)} производителей")

total_models = sum(len(m.get('models', [])) for m in mans.values())
print(f"Всего моделей в справочнике: {total_models}")

print("\nПримеры из справочника:")
for i, (mid, maker) in enumerate(list(mans.items())[:3]):
    name = maker.get('make_name')
    models = [m['model'] for m in maker.get('models', [])[:5]]
    print(f"  {name}: {models}")

conn.close()
