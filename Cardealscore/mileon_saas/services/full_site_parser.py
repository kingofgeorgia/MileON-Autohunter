#!/usr/bin/env python
"""Full myauto.ge site parser with progress tracking and delay support."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import cloudscraper
from fake_useragent import UserAgent


def load_manufacturers_and_models():
    """Load manufacturers and models from mansNModels.json."""
    mans_path = Path(__file__).parent.parent.parent / "mansNModels.json"
    make_names = {}
    model_names = {}
    
    if mans_path.exists():
        with mans_path.open("r", encoding="utf-8") as f:
            mans_data = json.load(f)
            
        # Build manufacturer names dictionary
        for man_id, man_data in mans_data.items():
            make_name = man_data.get("make_name", "")
            if make_name:
                make_names[int(man_id)] = make_name
            
            # Build model names dictionary
            models = man_data.get("models", [])
            for model in models:
                model_id = model.get("model_id")
                model_name = model.get("model", "")  
                if model_id and model_name:
                    model_names[int(model_id)] = model_name
    
    return make_names, model_names


# Load from mansNModels.json first, then fallback to hardcoded
_make_names_from_file, MODEL_NAMES = load_manufacturers_and_models()

# Use loaded names if available, otherwise use fallback
if _make_names_from_file:
    MAKE_NAMES = _make_names_from_file
else:
    # Fallback: Mapping of car manufacturer IDs to names
    MAKE_NAMES = {
    1: 'Alfa Romeo',
    2: 'Audi',
    3: 'BMW',
    5: 'Chevrolet',
    7: 'Ford',
    10: 'Dodge',
    11: 'GMC',
    12: 'Honda',
    14: 'Hyundai',
    16: 'Infiniti',
    18: 'Jaguar',
    19: 'Jeep',
    20: 'Kia',
    22: 'Land Rover',
    23: 'Lexus',
    24: 'Mazda',
    25: 'Mercedes-AMG',
    28: 'MINI',
    29: 'Mitsubishi',
    30: 'Nissan',
    31: 'Opel',
    33: 'Porsche',
    34: 'Renault',
    38: 'Skoda',
    39: 'Subaru',
    41: 'Toyota',
    42: 'Volkswagen',
    43: 'Volvo',
    53: 'Chrysler',
    61: 'Smart',
    75: 'Maserati',
    89: 'BYD',
    110: 'Hummer',
    124: 'Polestar',
    155: 'Tesla',
    161: 'Zeekr',
    394: 'Bentley',
    786: 'Alfa Romeo',
    987: 'Can-Am',
}


class FullSiteParser:
    """Parse all listings from myauto.ge with progress tracking and deduplication."""
    
    def __init__(
        self,
        delay_seconds: float = 2.0,
        progress_callback: Optional[Callable] = None,
        query_params: Optional[dict] = None,
        allowed_locations: Optional[set[int]] = None,
    ):
        """
        Initialize parser.
        
        Args:
            delay_seconds: Pause between requests to avoid blocking
            progress_callback: Function to call with (current, total, elapsed_time) for progress updates
        """
        self.delay_seconds = delay_seconds
        self.progress_callback = progress_callback
        self.scraper = cloudscraper.create_scraper()
        self.ua = UserAgent()
        self.base_url = "https://api2.myauto.ge/en/products"
        self.query_params = query_params
        self.allowed_locations = allowed_locations
        self.all_listings = []
        self.start_time = None
        self.existing_car_ids = set()  # Track existing car IDs for deduplication
        self.new_listings_count = 0    # Count of new listings added
        self.skipped_no_price_count = 0  # Count of listings skipped due to missing price
        self.make_names = MAKE_NAMES  # Load make names for lookup
        self.model_names = MODEL_NAMES  # Load model names for lookup
        
        self._setup_session()
    
    def _setup_session(self):
        """Configure scraper session."""
        self.scraper.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def _update_progress(self):
        """Call progress callback if provided."""
        if self.progress_callback and self.start_time:
            elapsed = time.time() - self.start_time
            self.progress_callback(self.new_listings_count, elapsed)
    
    def _load_existing_data(self):
        """Load existing car IDs from the merged JSON file (fallback to legacy files)."""
        self.existing_car_ids = set()

        merged_path = Path("full_site_merged.json")
        legacy_files = list(Path(".").glob("full_site_*.json"))
        files_to_read = [merged_path] if merged_path.exists() else legacy_files

        for json_file in files_to_read:
            try:
                with open(json_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                car_id = item.get("car_id")
                                if car_id:
                                    self.existing_car_ids.add(car_id)
            except Exception as exc:
                print(f"Warning: Could not read {json_file}: {exc}")

        if self.existing_car_ids:
            print(f"Loaded {len(self.existing_car_ids)} existing car IDs from previous saves")
    
    def _transform_listing(self, api_item: dict) -> dict:
        """Transform API response format to comprehensive format with all available fields."""
        make_id = api_item.get('man_id')
        make_name = MAKE_NAMES.get(make_id, f'Unknown ({make_id})')
        
        # Lookup model name from model_id
        model_id = api_item.get('model_id')
        model_name = self.model_names.get(model_id, '') if model_id else ''
        
        # If model not found in lookup, extract first word from car_model (trim field)
        trim = api_item.get('car_model', '')
        if not model_name and trim:
            # car_model usually contains: "ModelName Trim Options"
            # Example: "Pathfinder SE 4dr All-wheel Drive" or "Camaro 1LT RS"
            first_word = trim.split()[0] if trim.split() else ''
            model_name = first_word
        
        # Extract features (equipment indicators)
        features = {
            'abs': api_item.get('abs'),
            'esd': api_item.get('esd'),
            'el_windows': api_item.get('el_windows'),
            'conditioner': api_item.get('conditioner'),
            'leather': api_item.get('leather'),
            'disks': api_item.get('disks'),
            'nav_system': api_item.get('nav_system'),
            'central_lock': api_item.get('central_lock'),
            'hatch': api_item.get('hatch'),
            'right_wheel': api_item.get('right_wheel'),
            'alarm': api_item.get('alarm'),
            'board_comp': api_item.get('board_comp'),
            'hydraulics': api_item.get('hydraulics'),
            'chair_warming': api_item.get('chair_warming'),
            'climat_control': api_item.get('climat_control'),
            'obstacle_indicator': api_item.get('obstacle_indicator'),
        }
        
        metadata = {
            'man_id': api_item.get('man_id'),
            'model_id': api_item.get('model_id'),
            'status_id': api_item.get('status_id'),
            'user_id': api_item.get('user_id'),
            'dealer_user_id': api_item.get('dealer_user_id'),
            'pic_number': api_item.get('pic_number'),
            'price_value': api_item.get('price_value'),
            'gear_type_id': api_item.get('gear_type_id'),
            'drive_type_id': api_item.get('drive_type_id'),
            'door_type_id': api_item.get('door_type_id'),
            'color_id': api_item.get('color_id'),
            'airbags': api_item.get('airbags'),
            'price_value': api_item.get('price_value'),
            'fuel_type_id': api_item.get('fuel_type_id'),
            'tech_inspection': api_item.get('tech_inspection'),
            'predicted_price': api_item.get('predicted_price'),
            'pred_min_price': api_item.get('pred_min_price'),
            'pred_max_price': api_item.get('pred_max_price'),
            'views': api_item.get('views'),
            'daily_views': api_item.get('daily_views'),
            'order_date': api_item.get('order_date'),
            'changable': api_item.get('changable'),
            'for_rent': api_item.get('for_rent'),
            'rent_daily': api_item.get('rent_daily'),
            'rent_purchase': api_item.get('rent_purchase'),
        }
        
        return {
            "date": api_item.get('order_date', ''),
            "phone": api_item.get('client_phone', ''),
            "year": api_item.get('prod_year'),
            "engine_volume": api_item.get('engine_volume'),
            "price_usd": api_item.get('price_usd'),
            "location": api_item.get('location_id'),
            "location_id": api_item.get('location_id'),
            "model_id": api_item.get('model_id'),
            "model": model_name,
            "trim": trim,
            "photo_url": f"https://static.my.ge/myauto/photos/{api_item.get('photo', '')}/thumbs/{api_item.get('car_id')}_1.jpg" if api_item.get('photo') else '',
            "description": api_item.get('car_desc', ''),
            "car_id": api_item.get('car_id'),
            "make": api_item.get('man_id'),
            "make_name": make_name,
            "fuel_type": api_item.get('fuel_type_id'),
            "fuel_type_id": api_item.get('fuel_type_id'),
            "category": api_item.get('category_id'),
            "rating": 0.0,
            "status_id": api_item.get('status_id'),
            "user_id": api_item.get('user_id'),
            "dealer_user_id": api_item.get('dealer_user_id'),
            "customs_passed": api_item.get('customs_passed'),
            "doors": api_item.get('door_type_id'),
            "mileage_km": api_item.get('car_run_km'),
            "car_run_km": api_item.get('car_run_km'),
            "price_gel": api_item.get('price_value'),
            "features": features,
            "listing_metadata": metadata,
        }
    
    def parse_all_pages(self, max_pages: Optional[int] = None, skip_existing: bool = True) -> list[dict]:
        """
        Parse all pages from myauto.ge.
        
        Args:
            max_pages: Maximum pages to fetch (None for all pages)
            skip_existing: If True, skip listings that were already saved previously
        
        Returns:
            List of all new listings
        """
        self.all_listings = []
        self.new_listings_count = 0
        self.start_time = time.time()
        
        # Load existing data if deduplication is enabled
        if skip_existing:
            self._load_existing_data()
        
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
            
            try:
                # Fetch page
                params = self.query_params or {
                    'vehicleType': 0,
                    'hideDealPrice': 1,
                    'bargainType': 0,
                    'ForRent': '',
                    'Mans': '',
                    'PriceFrom': 600,
                    'PriceTo': 50000,
                    'CurrencyID': 1,
                    'MileageType': 1,
                    'Customs': 1,
                }
                params = dict(params)
                params['Page'] = page
                
                response = self.scraper.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Handle new API response format
                items = []
                if isinstance(data, dict):
                    # New format: {data: {items: [], meta: {}}, ...}
                    if 'data' in data and isinstance(data['data'], dict):
                        items = data['data'].get('items', [])
                    # Or items directly in data
                    elif 'items' in data:
                        items = data['items']
                elif isinstance(data, list):
                    # Old format: direct array
                    items = data
                
                if not items:
                    break
                
                # Transform items to standard format and add to collection
                for item in items:
                    car_id = item.get('car_id')
                    location_id = item.get('location_id')
                    price_usd = item.get('price_usd')

                    if self.allowed_locations and location_id not in self.allowed_locations:
                        continue
                    
                    # Skip if already exists
                    if skip_existing and car_id in self.existing_car_ids:
                        continue
                    
                    # Skip listings without valid price (API ignores hideDealPrice parameter sometimes)
                    if price_usd is None or price_usd == 0:
                        self.skipped_no_price_count += 1
                        continue
                    
                    transformed = self._transform_listing(item)
                    self.all_listings.append(transformed)
                    self.existing_car_ids.add(car_id)
                    self.new_listings_count += 1
                
                self._update_progress()
                
                # Check if this is last page (less than 20 items)
                if len(items) < 20:
                    break
                
                page += 1
                time.sleep(self.delay_seconds)  # Delay to avoid blocking
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        # Log summary if any listings were skipped due to missing price
        if self.skipped_no_price_count > 0:
            print(f"Skipped {self.skipped_no_price_count} listings without price")
        
        return self.all_listings
    
    def save_to_file(self, output_file: str = None) -> str:
        """
        Save parsed listings to JSON file.
        
        Args:
            output_file: Path to output file (defaults to full_site_YYYY_MM_DD_HH_MM_SS.json)
        
        Returns:
            Path to saved file
        """
        if not output_file:
            output_file = "full_site_merged.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        existing_items = []
        if output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        existing_items = [item for item in data if isinstance(item, dict)]
            except Exception as exc:
                print(f"Warning: Could not read {output_path}: {exc}")

        def entry_score(item: dict) -> int:
            return sum(1 for value in item.values() if value not in (None, "", [], {}))

        merged_by_id = {}
        for item in existing_items:
            car_id = item.get("car_id")
            if car_id is not None:
                merged_by_id[car_id] = item

        for item in self.all_listings:
            car_id = item.get("car_id")
            if car_id is None:
                continue
            if car_id in merged_by_id:
                current = merged_by_id[car_id]
                if entry_score(item) > entry_score(current):
                    merged_by_id[car_id] = item
            else:
                merged_by_id[car_id] = item

        merged_items = list(merged_by_id.values())

        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(merged_items, handle, ensure_ascii=False, indent=2)

        return str(output_path)
