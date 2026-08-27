import re

def validate_phone(phone):
    return bool(re.match(r'^\+?[1-9]\d{1,14}$', phone))


def validate_aadhaar(aadhaar):
    return len(str(aadhaar).strip()) == 12 and str(aadhaar).isdigit()


def lookup_pincode(pincode):
    """
    Given a 6-digit Indian pincode, returns a dictionary containing the corresponding state and district.
    Uses standard regional fallback mapping based on the first digit and common cities.
    """
    pincode = str(pincode).strip()
    
    # Common cities mappings
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
        
    if len(pincode) != 6 or not pincode.isdigit():
        return None
        
    # Region code fallback mappings
    first_digit = pincode[0]
    region_map = {
        '1': {'district': 'Northern District', 'state': 'Delhi/Haryana/Punjab'},
        '2': {'district': 'Central-Northern District', 'state': 'Uttar Pradesh/Uttarakhand'},
        '3': {'district': 'Western District', 'state': 'Gujarat/Rajasthan'},
        '4': {'district': 'West-Central District', 'state': 'Maharashtra/Madhya Pradesh'},
        '5': {'district': 'Southern District', 'state': 'Telangana/Andhra Pradesh/Karnataka'},
        '6': {'district': 'South-Eastern District', 'state': 'Tamil Nadu/Kerala'},
        '7': {'district': 'Eastern District', 'state': 'West Bengal/Odisha'},
        '8': {'district': 'North-Eastern District', 'state': 'Bihar/Jharkhand'},
        '9': {'district': 'Army Postal District', 'state': 'APS Fallback'},
    }
    
    return region_map.get(first_digit, {'district': 'Default District', 'state': 'Default State'})
