#!/usr/bin/env python
"""
Download official API data and create updated mansNModels.json with only active manufacturers.
"""

import json
import time
from pathlib import Path

from myauto_api import MyAutoAPI


def fetch_and_save_official_data():
    """Fetch all data from official API and save it."""
    
    print("=" * 80)
    print("📥 DOWNLOADING OFFICIAL DATA FROM API")
    print("=" * 80)
    
    api = MyAutoAPI()
    
    # Get all manufacturers
    print("\n🔄 Fetching manufacturers from API...")
    manufacturers = api.get_manufacturers()
    print(f"✅ Got {len(manufacturers)} manufacturers")
    
    # Build official structure
    official_data = {}
    
    for idx, man in enumerate(manufacturers, 1):
        man_id = man.man_id
        
        if idx % 20 == 0:
            print(f"  Processing {idx}/{len(manufacturers)}...", end='\r')
        
        try:
            models = api.get_models(man_id)
            
            model_list = [
                {
                    "model_id": m.model_id,
                    "model": m.title,
                }
                for m in models
            ]
            
            official_data[str(man_id)] = {
                "make_id": man_id,
                "make_name": man.title,
                "models": model_list,
            }
            
            time.sleep(0.01)  # Small delay to avoid rate limiting
            
        except Exception as e:
            print(f"\n⚠️  Error fetching models for {man.title}: {e}")
            official_data[str(man_id)] = {
                "make_id": man_id,
                "make_name": man.title,
                "models": [],
            }
    
    print(f"\n✅ Downloaded all {len(official_data)} manufacturers from API")
    
    # Count models
    total_models = sum(len(m.get("models", [])) for m in official_data.values())
    print(f"📊 Total models: {total_models}")
    
    # Save to file
    output_path = Path("mansNModels_official_api.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(official_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to {output_path}")
    
    return official_data


def compare_and_create_updated_version(official_data):
    """Compare with local data and create updated version."""
    
    print("\n" + "=" * 80)
    print("🔄 CREATING UPDATED mansNModels.json")
    print("=" * 80)
    
    # Load local data
    with open("mansNModels.json", encoding="utf-8") as f:
        local_data = json.load(f)
    
    # Create updated version with only active manufacturers
    updated_data = {}
    
    for man_id_str, api_man_data in official_data.items():
        man_id = int(man_id_str)
        
        # Check if we have local data for this manufacturer
        if man_id_str in local_data:
            local_man_data = local_data[man_id_str]
            
            # Use API models if we have them, otherwise use local
            if api_man_data["models"]:
                updated_data[man_id_str] = api_man_data
            else:
                updated_data[man_id_str] = local_man_data
        else:
            # New from API, add as is
            updated_data[man_id_str] = api_man_data
    
    print(f"\n✅ Created updated data with {len(updated_data)} manufacturers")
    
    # Count models
    total_models = sum(len(m.get("models", [])) for m in updated_data.values())
    print(f"📊 Total models: {total_models}")
    
    # Save backup of current
    backup_path = Path("mansNModels_backup_before_api_update.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(local_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Backed up current to {backup_path}")
    
    # Save updated version
    updated_path = Path("mansNModels_updated.json")
    with open(updated_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved updated version to {updated_path}")
    
    # Show statistics
    print(f"\n" + "=" * 80)
    print(f"📊 STATISTICS")
    print(f"=" * 80)
    print(f"  Original mansNModels.json: {len(local_data)} manufacturers")
    print(f"  Official API: {len(official_data)} manufacturers")
    print(f"  Updated version: {len(updated_data)} manufacturers")
    print(f"  Removed: {len(local_data) - len(updated_data)} manufacturers")
    
    # Models comparison
    orig_models = sum(len(m.get("models", [])) for m in local_data.values())
    api_models = sum(len(m.get("models", [])) for m in official_data.values())
    upd_models = sum(len(m.get("models", [])) for m in updated_data.values())
    
    print(f"\n  Original models: {orig_models}")
    print(f"  API models: {api_models}")
    print(f"  Updated models: {upd_models}")
    print(f"  Removed models: {orig_models - upd_models}")
    
    print(f"\n✅ Ready to use!")
    print(f"   To activate: mv mansNModels_updated.json mansNModels.json")


def main():
    try:
        # Download official data
        official_data = fetch_and_save_official_data()
        
        # Create updated version
        compare_and_create_updated_version(official_data)
        
        print(f"\n" + "=" * 80)
        print(f"✅ COMPLETE")
        print(f"=" * 80)
        print(f"""
Files created:
  • mansNModels_official_api.json - Raw data from official API
  • mansNModels_updated.json - Updated with only active manufacturers
  • mansNModels_backup_before_api_update.json - Backup of current data

Next steps:
  1. Review the changes
  2. If satisfied, replace: mv mansNModels_updated.json mansNModels.json
  3. Restart the application
""")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
