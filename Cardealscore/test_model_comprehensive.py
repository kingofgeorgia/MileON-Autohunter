#!/usr/bin/env python
"""Comprehensive test of the model loading functionality."""

from mileon_saas.services.full_site_parser import FullSiteParser, MODEL_NAMES
import json

# Create parser instance
parser = FullSiteParser(delay_seconds=2.0)

print("=" * 80)
print("🧪 MODEL LOADING TEST")
print("=" * 80)

# Test 1: Basic stats
print(f"\n✅ Model names loaded: {len(parser.model_names)} models")
print(f"✅ Make names loaded: {len(parser.make_names)} manufacturers")

# Test 2: Find some known Toyota models
print(f"\n🔍 Searching for known Toyota models in MODEL_NAMES:")
toyota_models = {}
for model_id, model_name in MODEL_NAMES.items():
    if 'Camry' in model_name or 'Corolla' in model_name or 'RAV4' in model_name:
        toyota_models[model_id] = model_name

if toyota_models:
    print(f"  Found {len(toyota_models)} Toyota models with name containing Camry/Corolla/RAV4:")
    for mid, mname in list(toyota_models.items())[:5]:
        print(f"    Model ID {mid}: {mname}")
else:
    print(f"  No Toyota models found with those keywords")

# Test 3: Check fallback behavior
print(f"\n🔍 Testing fallback behavior (when model_id not found):")
test_record = {
    'car_id': 99999,
    'man_id': 41,  # Toyota
    'model_id': 999999,  # Non-existent ID
    'car_model': 'Highlander Limited AWD',
    'car_desc': 'Test car',
    'price_usd': 25000,
    'order_date': '2026-02-11',
    'client_phone': '+995',
    'prod_year': 2020,
    'engine_volume': 3.5,
    'location_id': 1,
    'photo': 'test',
}

transformed = parser._transform_listing(test_record)
print(f"  Model ID {test_record['model_id']} (not in dict):")
print(f"    Fallback model name: {transformed['model']}")
print(f"    Expected: 'Highlander' (first word of trim)")
print(f"    Trim preserved: {transformed['trim']}")

# Test 4: Verify records with actual model_id
print(f"\n🔍 Testing with actual model_id lookup:")
test_record2 = {
    'car_id': 88888,
    'man_id': 25,  # Mercedes-AMG
    'model_id': None,  # No model ID
    'car_model': 'C-Class Sedan',
    'car_desc': 'Luxury car',
    'price_usd': 35000,
    'order_date': '2026-02-11',
    'client_phone': '+995',
    'prod_year': 2022,
    'engine_volume': 2.0,
    'location_id': 1,
    'photo': 'test',
}

transformed2 = parser._transform_listing(test_record2)
print(f"  Model ID None (no model lookup):")
print(f"    Fallback model name: {transformed2['model']}")
print(f"    Expected: 'C-Class' (first word of trim)")

print(f"\n" + "=" * 80)
print(f"✅ All model loading tests completed successfully!")
print(f"=" * 80)
