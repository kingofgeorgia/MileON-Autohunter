#!/usr/bin/env python
"""
Fresh import script: Delete old database and prepare for new import via GUI.
This script:
1. Deletes the old sqlite database
2. The next time GUI starts, it will show fresh import option

To use:
1. Run this script
2. Open GUI and click "Import Full Site" button to start fresh import with proper model names
"""

import time
from pathlib import Path
import sqlite3


def main():
    print("=" * 80)
    print("🔄 FRESH IMPORT SETUP: Deleting old database")
    print("=" * 80)
    
    db_path = Path("mileon_saas.db")
    
    # Step 1: Delete old database
    if db_path.exists():
        file_size_mb = db_path.stat().st_size / 1024 / 1024
        print(f"\n📁 Found old database: {db_path} ({file_size_mb:.1f} MB)")
        print(f"🗑️  Deleting old database...")
        db_path.unlink()
        print(f"✅ Old database deleted")
    else:
        print(f"\n✅ No existing database found")
    
    # Step 2: Delete old merged files
    merged_files = list(Path(".").glob("full_site_*.json"))
    if merged_files:
        print(f"\n📁 Found {len(merged_files)} old merged files:")
        for f in merged_files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.1f} MB)")
        
        print(f"🗑️  Deleting old files...")
        for f in merged_files:
            f.unlink()
        print(f"✅ Old merged files deleted")
    
    print(f"\n" + "=" * 80)
    print(f"✅ Database and files cleaned up!")
    print(f"\n📝 Next steps:")
    print(f"  1. Open GUI or run: python main.py")
    print(f"  2. Click 'Import Full Site' button")
    print(f"  3. The import will use the NEW MODEL_NAMES loading from full_site_parser.py")
    print(f"  4. All 10,554 model names will be properly resolved from mansNModels.json")
    print(f"=" * 80)


if __name__ == "__main__":
    main()

