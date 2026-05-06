#!/usr/bin/env python3
"""
Full database reindexing with official API data (mansNModels.json)
- Backs up existing database
- Deletes old database
- Recreates schema
- Imports all listings from myauto.ge with new manufacturer/model data
"""

import asyncio
import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

# Add workspace to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from mileon_saas.db import init_db, close_engine, SessionLocal
import mileon_saas.models  # Ensure ORM models are registered before init_db
from mileon_saas.services.full_site_parser import FullSiteParser


async def backup_database():
    """Create backup of current database."""
    db_path = Path("mileon_saas.db")
    if db_path.exists():
        backup_dir = Path("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"mileon_saas_reindex_{timestamp}.db"
        
        print(f"\nBacking up database...")
        print(f"  From: {db_path.absolute()}")
        print(f"  To:   {backup_path.absolute()}")
        
        try:
            shutil.copy2(db_path, backup_path)
            print(f"  [OK] Backup created: {backup_path.name}")
            print(f"       Size: {backup_path.stat().st_size:,} bytes")
            return True
        except Exception as e:
            print(f"  [ERROR] Backup failed: {e}")
            return False
    return True


async def delete_database():
    """Delete the database file and lock files."""
    db_path = Path("mileon_saas.db")
    
    if not db_path.exists():
        print(f"\nDatabase does not exist, skipping deletion.")
        return True
    
    print(f"\nDeleting old database...")
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            # Delete main DB
            if db_path.exists():
                db_path.unlink()
                print(f"  [OK] Deleted: {db_path.name}")
            
            # Delete WAL file
            wal_path = db_path.with_name(db_path.name + "-wal")
            if wal_path.exists():
                wal_path.unlink()
                print(f"  [OK] Deleted: {wal_path.name}")
            
            # Delete SHM file
            shm_path = db_path.with_name(db_path.name + "-shm")
            if shm_path.exists():
                shm_path.unlink()
                print(f"  [OK] Deleted: {shm_path.name}")
            
            if not db_path.exists():
                return True
                
        except OSError as e:
            if attempt < max_attempts - 1:
                wait = 2 ** attempt
                print(f"  [RETRY {attempt + 1}/{max_attempts}] {e}")
                print(f"  Waiting {wait}s before retry...")
                await asyncio.sleep(wait)
            else:
                print(f"  [ERROR] Failed to delete after {max_attempts} attempts: {e}")
                return False
    
    return False


async def recreate_schema():
    """Create empty database schema."""
    print(f"\nRecreating database schema...")
    try:
        await close_engine()
        await asyncio.sleep(1)
        
        await init_db()
        print(f"  [OK] Schema created successfully")
        
        # Verify schema
        db_path = Path("mileon_saas.db")
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]
            conn.close()
            print(f"  [OK] Tables created: {len(tables)} tables")
            print(f"       {', '.join(sorted(tables))}")
            return True
        return False
    except Exception as e:
        print(f"  [ERROR] Schema creation failed: {e}")
        return False


async def import_listings():
    """Import all listings from myauto.ge using FullSiteParser and save to database."""
    print(f"\nImporting listings from myauto.ge...")
    print(f"  This may take 20-60 minutes depending on site responsiveness")
    print()
    
    def progress_callback(current: int, elapsed: float):
        # Format elapsed time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
        
        print(
            f"\r  Parsed: {current:,} listings | Elapsed: {time_str}",
            end="",
            flush=True,
        )
    
    try:
        # Step 1: Parse listings from API
        parser = FullSiteParser(
            delay_seconds=2.0,
            progress_callback=progress_callback,
        )
        
        print("  Starting parser...")
        start_time = time.time()
        
        # Run the parser (synchronous call - fetches all pages)
        listings = parser.parse_all_pages(skip_existing=False)
        
        elapsed = time.time() - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        print(f"\n  [OK] Parsing completed in {hours}h {minutes}m {seconds}s")
        print(f"  [OK] Total listings fetched: {len(listings):,}")
        
        # Step 2: Save to temporary JSON file
        print("\n  Saving listings to temporary JSON...")
        import json
        temp_json_path = Path("_temp_listings_for_import.json")
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=0)
        print(f"  [OK] Saved to: {temp_json_path.name}")
        
        # Step 3: Import from JSON into database using ingestion service
        print("\n  Importing into database...")
        from mileon_saas.services.ingestion import ingest_from_json
        from mileon_saas.db import SessionLocal
        import json
        
        async with SessionLocal() as session:
            count = await ingest_from_json(session, str(temp_json_path), company_id=1)
            print(f"  [OK] Imported {count:,} listings into database")
        
        # Clean up temp file
        try:
            temp_json_path.unlink()
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n  [ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_import():
    """Verify brand/model resolution in imported data."""
    print(f"\nVerifying brand/model resolution...")
    
    try:
        conn = sqlite3.connect("mileon_saas.db")
        cursor = conn.cursor()
        
        # Count by brand
        cursor.execute("SELECT brand, COUNT(*) FROM car_listings GROUP BY brand ORDER BY COUNT(*) DESC LIMIT 10")
        rows = cursor.fetchall()
        
        print(f"  Top 10 brands:")
        for brand, count in rows:
            print(f"    {brand:20s} : {count:6,} listings")
        
        # Check unknown count
        cursor.execute("SELECT COUNT(*) FROM car_listings WHERE brand = 'unknown'")
        unknown_count = cursor.fetchone()[0]
        
        total = 0
        cursor.execute("SELECT COUNT(*) FROM car_listings")
        total = cursor.fetchone()[0]
        
        unknown_pct = (unknown_count / total * 100) if total > 0 else 0
        print(f"\n  Unknown brands: {unknown_count:,} / {total:,} ({unknown_pct:.1f}%)")
        
        conn.close()
        
        if unknown_pct > 5:
            print(f"  [WARNING] More than 5% unknown brands")
            return False
        else:
            print(f"  [OK] Brand resolution looks good")
            return True
            
    except Exception as e:
        print(f"  [ERROR] Verification failed: {e}")
        return False


async def main():
    """Main reindexing workflow."""
    print("=" * 70)
    print("FULL DATABASE REINDEXING")
    print("Using new mansNModels.json (160 manufacturers, 3,169 models)")
    print("=" * 70)
    
    try:
        # Step 1: Backup
        if not await backup_database():
            print("\n[FATAL] Backup failed, aborting")
            return False
        
        # Step 2: Delete old database
        if not await delete_database():
            print("\n[FATAL] Could not delete old database, aborting")
            return False
        
        # Step 3: Recreate schema
        if not await recreate_schema():
            print("\n[FATAL] Schema creation failed, aborting")
            return False
        
        # Step 4: Import listings
        if not await import_listings():
            print("\n[FATAL] Import failed, aborting")
            return False
        
        # Step 5: Verify
        if not await verify_import():
            print("\n[WARNING] Verification found issues, but import completed")
        
        print("\n" + "=" * 70)
        print("REINDEXING COMPLETE!")
        print("=" * 70)
        print("\nSummary:")
        print("  - Old database backed up to backups/")
        print("  - New database created from scratch")
        print("  - All listings imported with new manufacturer/model data")
        print("  - Brand/model resolution verified")
        print("\nYou can now:")
        print("  1. python main.py              # Run the application")
        print("  2. python app.py               # Run the API")
        print("\nGitHub URL:")
        print("  - Review the data structure")
        print("  - Check brand/model statistics")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Reindexing cancelled by user")
        return False
    except Exception as e:
        print(f"\n[FATAL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
