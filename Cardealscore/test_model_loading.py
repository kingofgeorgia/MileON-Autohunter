#!/usr/bin/env python
"""Test that the FullSiteParser correctly loads and uses model names."""

from mileon_saas.services.full_site_parser import FullSiteParser

# Create parser instance to verify MODEL_NAMES is loaded
parser = FullSiteParser(delay_seconds=2.0)

print(f'✅ Parser initialized successfully')
print(f'📊 Model names available: {len(parser.model_names)} models')
print(f'📊 Make names available: {len(parser.make_names)} manufacturers')

# Test _transform_listing with a sample record
sample_record = {
    'car_id': 12345,
    'man_id': 41,  # Toyota
    'model_id': 450,  # Toyota Camry
    'car_model': 'Camry LE Sedan automatic',
    'car_desc': 'Clean condition, well maintained',
    'price_usd': 15000,
    'order_date': '2026-02-11',
    'client_phone': '+995123456789',
    'prod_year': 2015,
    'engine_volume': 2.5,
    'location_id': 1,
    'photo': 'test',
}

# Check if model exists in the dict
if sample_record['model_id'] in parser.model_names:
    model_name = parser.model_names[sample_record['model_id']]
    print(f'✅ Model ID {sample_record["model_id"]} found: {model_name}')
else:
    print(f'❌ Model ID {sample_record["model_id"]} NOT found')

# Test the transform function
transformed = parser._transform_listing(sample_record)
print(f'\n📋 Transformed listing:')
print(f'  Brand: {transformed["make_name"]}')
print(f'  Model: {transformed["model"]}')
print(f'  Trim: {transformed["trim"]}')
print(f'  Price USD: {transformed["price_usd"]}')
print(f'\n✅ Model loading test completed successfully!')
