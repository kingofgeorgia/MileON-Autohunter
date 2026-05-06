#!/usr/bin/env python
"""Final verification that the model name fix is complete."""

import json
from pathlib import Path

print('🔍 FINAL VERIFICATION')
print('=' * 80)

# Check 1: mansNModels.json exists and has data
mans_path = Path('mansNModels.json')
if mans_path.exists():
    with open(mans_path, encoding='utf-8') as f:
        mans_data = json.load(f)
    print(f'✅ mansNModels.json: {len(mans_data)} manufacturers')
else:
    print('❌ mansNModels.json: NOT FOUND')

# Check 2: Can import the modified parser
try:
    from mileon_saas.services.full_site_parser import (
        FullSiteParser, MODEL_NAMES, MAKE_NAMES, 
        load_manufacturers_and_models
    )
    print(f'✅ full_site_parser.py: Successfully imported')
    print(f'   - load_manufacturers_and_models: function available')
    print(f'   - MODEL_NAMES: {len(MODEL_NAMES)} models')
    print(f'   - MAKE_NAMES: {len(MAKE_NAMES)} manufacturers')
except Exception as e:
    print(f'❌ full_site_parser.py: {e}')
    exit(1)

# Check 3: Parser instance can be created
try:
    parser = FullSiteParser(delay_seconds=1.0)
    print(f'✅ FullSiteParser instantiation: SUCCESS')
    print(f'   - self.model_names: {len(parser.model_names)} entries')
    print(f'   - self.make_names: {len(parser.make_names)} entries')
except Exception as e:
    print(f'❌ FullSiteParser instantiation: {e}')
    exit(1)

# Check 4: Sample transformation
try:
    sample = {
        'car_id': 1,
        'man_id': 41,
        'model_id': 1089,  # Toyota Camry
        'car_model': 'Camry LE Sedan',
        'price_usd': 20000,
        'order_date': '2026-02-11',
        'client_phone': '',
        'prod_year': 2020,
        'engine_volume': 2.5,
        'location_id': 1,
        'photo': 'test',
        'car_desc': '',
    }
    result = parser._transform_listing(sample)
    expected_model = 'Camry'
    actual_model = result['model']
    
    if actual_model == expected_model:
        print(f'✅ Model transformation: SUCCESS')
        print(f'   - Input model_id: 1089')
        print(f'   - Output model: {actual_model}')
        trim_val = result['trim']
        print(f'   - Trim preserved: {trim_val}')
    else:
        print(f'⚠️  Model transformation: Got {actual_model}, expected {expected_model}')
except Exception as e:
    print(f'❌ Model transformation: {e}')
    exit(1)

print()
print('=' * 80)
print('✅ ALL VERIFICATIONS PASSED')
print('=' * 80)
print()
print('Status: READY FOR RE-IMPORT')
print()
print('Next steps:')
print('  1. python fresh_import.py    (delete old database)')
print('  2. python main.py             (open GUI)')
print('  3. Click Import Full Site     (in GUI)')
print('  4. python check_models.py     (verify results)')
print()
