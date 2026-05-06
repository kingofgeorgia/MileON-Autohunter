#!/usr/bin/env python
"""
Fetch official brands and models from myauto.ge API and compare with local data.
"""

import json
import time
from pathlib import Path
from collections import defaultdict

from myauto_api import MyAutoAPI, VehicleType


def fetch_official_data():
    """Fetch all manufacturers and models from official API."""
    print("=" * 80)
    print("🌐 FETCHING OFFICIAL DATA FROM myauto.ge API")
    print("=" * 80)
    
    api = MyAutoAPI()
    
    # Get all manufacturers
    print("\n📥 Fetching manufacturers...")
    manufacturers = api.get_manufacturers()
    print(f"✅ Fetched {len(manufacturers)} manufacturers")
    
    # Build official data structure
    official_data = {}
    
    for idx, man in enumerate(manufacturers, 1):
        if idx % 100 == 0:
            print(f"  Processing manufacturer {idx}/{len(manufacturers)}...", end='\r')
        
        man_id = man.man_id
        man_title = man.title
        
        # Get models for this manufacturer
        try:
            models = api.get_models(man_id)
            model_list = []
            for model in models:
                model_list.append({
                    "model_id": model.model_id,
                    "model": model.title,
                })
            
            official_data[str(man_id)] = {
                "make_id": man_id,
                "make_name": man_title,
                "models": model_list,
            }
            
            time.sleep(0.01)  # Small delay to avoid rate limiting
            
        except Exception as e:
            print(f"\n⚠️  Error fetching models for {man_title} (ID: {man_id}): {e}")
            official_data[str(man_id)] = {
                "make_id": man_id,
                "make_name": man_title,
                "models": [],
            }
    
    print(f"\n✅ Processed all {len(official_data)} manufacturers")
    
    # Count total models
    total_models = sum(len(m.get("models", [])) for m in official_data.values())
    print(f"📊 Total models in API: {total_models}")
    
    return official_data


def load_local_data():
    """Load our local mansNModels.json."""
    print("\n📂 Loading local mansNModels.json...")
    
    path = Path("mansNModels.json")
    if not path.exists():
        print("❌ mansNModels.json not found!")
        return {}
    
    with open(path, encoding='utf-8') as f:
        local_data = json.load(f)
    
    print(f"✅ Loaded {len(local_data)} manufacturers")
    
    # Count total models
    total_models = sum(len(m.get("models", [])) for m in local_data.values())
    print(f"📊 Total models in local data: {total_models}")
    
    return local_data


def compare_data(official, local):
    """Compare official API data with local data."""
    print("\n" + "=" * 80)
    print("📊 COMPARISON: OFFICIAL vs LOCAL DATA")
    print("=" * 80)
    
    # Convert local man_ids to strings for comparison
    local_keys = set(str(k) if isinstance(k, int) else k for k in local.keys())
    official_keys = set(official.keys())
    
    # Find differences
    new_makes = official_keys - local_keys
    removed_makes = local_keys - official_keys
    common_makes = local_keys & official_keys
    
    print(f"\n📈 MANUFACTURER STATISTICS:")
    print(f"  • Official API: {len(official_keys)} manufacturers")
    print(f"  • Local data: {len(local_keys)} manufacturers")
    print(f"  • Common: {len(common_makes)}")
    print(f"  • New in API: {len(new_makes)}")
    print(f"  • Removed from API: {len(removed_makes)}")
    
    # Show new manufacturers
    if new_makes:
        print(f"\n🆕 NEW MANUFACTURERS IN API ({len(new_makes)}):")
        for man_id in sorted(new_makes, key=lambda x: int(x)):
            man_data = official[man_id]
            make_name = man_data.get("make_name", "Unknown")
            model_count = len(man_data.get("models", []))
            print(f"  • {make_name:30} (ID: {man_id:3}) - {model_count} models")
    
    # Show removed manufacturers
    if removed_makes:
        print(f"\n❌ REMOVED FROM API ({len(removed_makes)}):")
        for man_id in sorted(removed_makes, key=lambda x: int(x)):
            man_data = local[man_id]
            make_name = man_data.get("make_name", "Unknown")
            model_count = len(man_data.get("models", []))
            print(f"  • {make_name:30} (ID: {man_id:3}) - {model_count} models")
    
    # Compare models for common manufacturers
    print(f"\n🔄 MODEL CHANGES IN COMMON MANUFACTURERS:")
    
    model_stats = {
        "new": 0,
        "removed": 0,
        "updated": 0,
        "unchanged": 0,
    }
    
    updated_makes = {}
    
    for man_id in sorted(common_makes, key=lambda x: int(x)):
        official_man = official[man_id]
        local_man = local[man_id]
        
        official_models = {m["model_id"]: m["model"] for m in official_man.get("models", [])}
        local_models = {m["model_id"]: m["model"] for m in local_man.get("models", [])}
        
        official_model_ids = set(official_models.keys())
        local_model_ids = set(local_models.keys())
        
        new_models = official_model_ids - local_model_ids
        removed_models = local_model_ids - official_model_ids
        updated_models = []
        unchanged = 0
        
        for model_id in official_model_ids & local_model_ids:
            if official_models[model_id] != local_models[model_id]:
                updated_models.append((model_id, local_models[model_id], official_models[model_id]))
            else:
                unchanged += 1
        
        if new_models or removed_models or updated_models:
            make_name = official_man.get("make_name", "Unknown")
            updated_makes[man_id] = {
                "make_name": make_name,
                "new": len(new_models),
                "removed": len(removed_models),
                "updated": len(updated_models),
                "unchanged": unchanged,
                "new_models": new_models,
                "removed_models": removed_models,
                "updated_models": updated_models,
            }
            
            model_stats["new"] += len(new_models)
            model_stats["removed"] += len(removed_models)
            model_stats["updated"] += len(updated_models)
            model_stats["unchanged"] += unchanged
    
    # Show summary statistics
    print(f"\n  📊 SUMMARY:")
    print(f"    • New models: {model_stats['new']}")
    print(f"    • Removed models: {model_stats['removed']}")
    print(f"    • Updated models: {model_stats['updated']}")
    print(f"    • Unchanged: {model_stats['unchanged']}")
    
    # Show details for manufacturers with changes
    if updated_makes:
        print(f"\n  🔧 MANUFACTURERS WITH MODEL CHANGES ({len(updated_makes)}):")
        for man_id in sorted(updated_makes.keys(), key=lambda x: int(x)):
            info = updated_makes[man_id]
            make_name = info["make_name"]
            changes = []
            if info["new"] > 0:
                changes.append(f"+{info['new']}")
            if info["removed"] > 0:
                changes.append(f"-{info['removed']}")
            if info["updated"] > 0:
                changes.append(f"~{info['updated']}")
            
            change_str = " ".join(changes)
            print(f"    • {make_name:30} {change_str:15} (ID: {man_id})")
    
    return {
        "new_makes": new_makes,
        "removed_makes": removed_makes,
        "model_stats": model_stats,
        "updated_makes": updated_makes,
    }


def save_comparison_report(official, local, comparison):
    """Save detailed comparison report to file."""
    print("\n" + "=" * 80)
    print("💾 SAVING DETAILED REPORT")
    print("=" * 80)
    
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "official_manufacturers": len(official),
            "local_manufacturers": len(local),
            "new_manufacturers": len(comparison["new_makes"]),
            "removed_manufacturers": len(comparison["removed_makes"]),
            "new_models": comparison["model_stats"]["new"],
            "removed_models": comparison["model_stats"]["removed"],
            "updated_models": comparison["model_stats"]["updated"],
        },
        "new_manufacturers": [
            {
                "id": man_id,
                "name": official[man_id].get("make_name"),
                "model_count": len(official[man_id].get("models", [])),
            }
            for man_id in sorted(comparison["new_makes"], key=lambda x: int(x))
        ],
        "removed_manufacturers": [
            {
                "id": man_id,
                "name": local[man_id].get("make_name"),
                "model_count": len(local[man_id].get("models", [])),
            }
            for man_id in sorted(comparison["removed_makes"], key=lambda x: int(x))
        ],
    }
    
    report_path = Path("api_comparison_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Report saved: {report_path}")
    
    return report


def main():
    try:
        # Fetch official data
        official_data = fetch_official_data()
        
        # Load local data
        local_data = load_local_data()
        
        # Compare
        comparison = compare_data(official_data, local_data)
        
        # Save report
        report = save_comparison_report(official_data, local_data, comparison)
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ COMPARISON COMPLETE")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  • Official API vs Local data")
        print(f"  • New manufacturers: {len(comparison['new_makes'])}")
        print(f"  • Removed manufacturers: {len(comparison['removed_makes'])}")
        print(f"  • New models: {comparison['model_stats']['new']}")
        print(f"  • Removed models: {comparison['model_stats']['removed']}")
        print(f"  • Updated models: {comparison['model_stats']['updated']}")
        print(f"\nRecommendations:")
        if comparison['new_makes'] or comparison['model_stats']['new'] > 100:
            print(f"  • 🔄 Consider updating mansNModels.json with new data from API")
        if comparison['removed_makes'] or comparison['model_stats']['removed'] > 50:
            print(f"  • 🧹 Consider removing obsolete manufacturers/models")
        if not comparison['new_makes'] and not comparison['removed_makes'] and comparison['model_stats']['new'] < 10:
            print(f"  • ✅ Data is up-to-date!")
        
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
