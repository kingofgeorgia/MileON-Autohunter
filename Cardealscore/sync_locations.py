"""
Скрипт для синхронизации локаций с официального API MyAuto
Создает locations.json со всеми локациями для использования в проекте
"""

import json
from pathlib import Path
from myauto_api import MyAutoAPI


def fetch_and_save_locations():
    """Загружает локации из API и сохраняет в JSON."""
    api = MyAutoAPI(language="en")  # English language
    
    print("Fetching locations from MyAuto API (English)...")
    locations = api.get_locations()
    
    # Создаем два формата: словарь и список
    locations_dict = {}
    locations_list = []
    
    for location in locations:
        locations_dict[str(location.location_id)] = location.title
        locations_list.append({
            "location_id": location.location_id,
            "title": location.title
        })
    
    # Сохраняем словарь для быстрого доступа по ID
    dict_path = Path("locations.json")
    with dict_path.open("w", encoding="utf-8") as f:
        json.dump(locations_dict, f, ensure_ascii=False, indent=2)
    
    # Сохраняем список для полных данных
    list_path = Path("locations_full.json")
    with list_path.open("w", encoding="utf-8") as f:
        json.dump(locations_list, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved {len(locations)} locations to:")
    print(f"   - {dict_path.absolute()} (ID -> name mapping)")
    print(f"   - {list_path.absolute()} (full data)")
    
    # Показываем примеры
    print(f"\nSample locations:")
    for i, location in enumerate(locations[:10]):
        print(f"  {location.location_id}: {location.title}")
    
    return locations_dict


if __name__ == "__main__":
    fetch_and_save_locations()
