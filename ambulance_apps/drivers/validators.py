import re
import urllib.request
import json
from django.core.cache import cache

def validate_phone(phone):
    return bool(re.match(r'^\+?[1-9]\d{1,14}$', phone))


def validate_aadhaar(aadhaar):
    return len(str(aadhaar).strip()) == 12 and str(aadhaar).isdigit()


def lookup_pincode(pincode):
    """
    Given a 6-digit Indian pincode, returns a dictionary containing the corresponding state and district.
    Queries the official Indian Postal API with cache/fallback.
    """
    pincode = str(pincode).strip()
    if len(pincode) != 6 or not pincode.isdigit():
        return None

    # Check cache
    cache_key = f"pincode_lookup_{pincode}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 1. Try Indian Postal API
    try:
        req = urllib.request.Request(
            f"https://api.postalpincode.in/pincode/{pincode}",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data and isinstance(data, list) and data[0].get('Status') == 'Success':
                    post_offices = data[0].get('PostOffice', [])
                    if post_offices:
                        res = {
                            'district': post_offices[0].get('District'),
                            'state': post_offices[0].get('State')
                        }
                        cache.set(cache_key, res, timeout=86400)
                        return res
    except Exception as e:
        print(f"Postal API lookup failed, falling back to local mapping: {e}")

    # 2. Common cities mappings
    mappings = {
        '400018': {'district': 'Mumbai', 'state': 'Maharashtra'},
        '400001': {'district': 'Mumbai', 'state': 'Maharashtra'},
        '110001': {'district': 'New Delhi', 'state': 'Delhi'},
        '411001': {'district': 'Pune', 'state': 'Maharashtra'},
        '560001': {'district': 'Bengaluru', 'state': 'Karnataka'},
        '600001': {'district': 'Chennai', 'state': 'Tamil Nadu'},
        '700001': {'district': 'Kolkata', 'state': 'West Bengal'},
        '500001': {'district': 'Hyderabad', 'state': 'Telangana'},
    }
    
    if pincode in mappings:
        return mappings[pincode]

    # 3. Region code fallback mappings
    first_digit = pincode[0]
    region_map = {
        '1': {'district': 'Northern District', 'state': 'Delhi/Haryana/Punjab'},
        '2': {'district': 'Central-Northern District', 'state': 'Uttar Pradesh'},
        '3': {'district': 'Western District', 'state': 'Gujarat/Rajasthan'},
        '4': {'district': 'West-Central District', 'state': 'Maharashtra/Madhya Pradesh'},
        '5': {'district': 'Southern District', 'state': 'Telangana/Andhra Pradesh/Karnataka'},
        '6': {'district': 'South-Eastern District', 'state': 'Tamil Nadu/Kerala'},
        '7': {'district': 'Eastern District', 'state': 'West Bengal/Odisha'},
        '8': {'district': 'North-Eastern District', 'state': 'Bihar/Jharkhand'},
        '9': {'district': 'Army Postal District', 'state': 'APS Fallback'},
    }
    
    return region_map.get(first_digit, {'district': 'Default District', 'state': 'Default State'})
