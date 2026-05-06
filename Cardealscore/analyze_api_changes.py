#!/usr/bin/env python
"""
Analyze which manufacturers are still relevant for cars.
The API data shows only car-relevant manufacturers.
"""

import json
from pathlib import Path
from collections import defaultdict


def analyze_changes():
    """Analyze what was removed and what is still active."""
    
    print("=" * 80)
    print("🔍 ANALYZING API DATA CHANGES")
    print("=" * 80)
    
    # Load the comparison report
    with open("api_comparison_report.json", encoding="utf-8") as f:
        report = json.load(f)
    
    summary = report["summary"]
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Official API manufacturers: {summary['official_manufacturers']}")
    print(f"  Our local manufacturers: {summary['local_manufacturers']}")
    print(f"  Removed from our list: {summary['removed_manufacturers']}")
    print(f"  Removed models: {summary['removed_models']}")
    print(f"  Updated models: {summary['updated_models']}")
    
    # Categorize removed manufacturers
    removed = report["removed_manufacturers"]
    
    # Categorization keywords
    categories = {
        "Motorcycles": ["Yamaha", "Kawasaki", "Ducati", "Harley", "KTM", "Aprilia", "Honda", 
                       "Suzuki", "Triumph", "Cagiva", "Jawa", "Polaris", "BRP", "Husqvarna"],
        "Trucks/Buses": ["Scania", "MAN", "DAF", "MAZ", "KRAZ", "Setra", "Neoplan", "Kamaz", "ZIL"],
        "Heavy Equipment": ["Caterpillar", "JCB", "Bobcat", "Komatsu", "Terex", "Liebherr", "Hidromek", "Zoomlion"],
        "Agricultural": ["New Holland", "Massey Ferguson", "Belarus", "Case", "Claas", "Branson", "Deutz Fahr"],
        "Construction": ["Fiat-Hitachi", "Fermec", "Lintex"],
        "Other": [],
    }
    
    categorized = defaultdict(list)
    for removed_man in removed:
        man_name = removed_man["name"]
        man_id = removed_man["id"]
        model_count = removed_man["model_count"]
        
        found = False
        for category, keywords in categories.items():
            if category == "Other":
                continue
            if any(keyword.lower() in man_name.lower() for keyword in keywords):
                categorized[category].append({
                    "id": man_id,
                    "name": man_name,
                    "models": model_count
                })
                found = True
                break
        
        if not found:
            categorized["Other"].append({
                "id": man_id,
                "name": man_name,
                "models": model_count
            })
    
    print(f"\n📋 REMOVED MANUFACTURERS BY CATEGORY:")
    total_removed_models = 0
    for category in sorted(categorized.keys()):
        items = categorized[category]
        if not items:
            continue
        
        total_models = sum(item["models"] for item in items)
        total_removed_models += total_models
        
        print(f"\n  {category}: {len(items)} manufacturers, {total_models} models")
        for item in sorted(items, key=lambda x: -x["models"])[:5]:  # Show top 5
            print(f"    • {item['name']:30} - {item['models']} models")
        
        if len(items) > 5:
            remaining = len(items) - 5
            print(f"    ... and {remaining} more ...")
    
    print(f"\n  Total removed: {total_removed_models} models")
    
    # Now let's see what's left in the API
    with open("mansNModels.json", encoding="utf-8") as f:
        local_data = json.load(f)
    
    # Get IDs of removed manufacturers
    removed_ids = {int(r["id"]) for r in removed}
    
    # Show what's active (still in API)
    print(f"\n✅ ACTIVE MANUFACTURERS IN API ({summary['official_manufacturers']}):")
    
    active = []
    for man_id_str, man_data in local_data.items():
        man_id = int(man_id_str)
        if man_id not in removed_ids:
            active.append({
                "id": man_id,
                "name": man_data.get("make_name", "Unknown"),
                "models": len(man_data.get("models", [])),
            })
    
    active_sorted = sorted(active, key=lambda x: -x["models"])
    
    print(f"\n  Top 30 manufacturers by model count:")
    for idx, item in enumerate(active_sorted[:30], 1):
        print(f"  {idx:2}. {item['name']:30} - {item['models']:4} models (ID: {item['id']})")
    
    if len(active_sorted) > 30:
        print(f"  ... and {len(active_sorted) - 30} more")
    
    # Summary
    print(f"\n" + "=" * 80)
    print(f"📈 CONCLUSION:")
    print(f"=" * 80)
    print(f"""
The API has filtered down to {summary['official_manufacturers']} manufacturers,
removing {summary['removed_manufacturers']} brands that were in our database.

The removed brands are primarily:
  • Motorcycles (Yamaha, Kawasaki, Ducati, etc.)
  • Trucks & buses (Scania, MAN, DAF, etc.)
  • Heavy construction equipment (Caterpillar, JCB, Komatsu, etc.)
  • Agricultural equipment (New Holland, Case, etc.)

The API now focuses on CARS only, which makes sense for the myauto.ge 
car marketplace business model.

🔧 RECOMMENDATION:
  • Keep mansNModels.json as is (it has useful historical data)
  • Use only the {summary['official_manufacturers']} active manufacturers for:
    - API queries
    - Database imports
    - Vehicle filtering
  • Filter out motorcycle/truck/equipment categories

This ensures we stay aligned with official API data.
""")


if __name__ == "__main__":
    analyze_changes()
