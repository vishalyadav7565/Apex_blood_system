import logging
import requests

logger = logging.getLogger(__name__)

# In-memory cache for resolved pincodes
_PINCODE_CACHE = {}


def lookup_pincode(pincode):
    """
    Looks up Indian Postal Pincode details from api.postalpincode.in.
    Returns a dict with state, district, city, post_offices, or None.
    """
    if not pincode:
        return None
    p = str(pincode).strip()
    if len(p) != 6 or not p.isdigit():
        return None

    if p in _PINCODE_CACHE:
        return _PINCODE_CACHE[p]

    try:
        resp = requests.get(f"https://api.postalpincode.in/pincode/{p}", timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if first.get("Status") == "Success" and first.get("PostOffice"):
                    po = first["PostOffice"][0]
                    district = (po.get("District") or "").strip()
                    state = (po.get("State") or "").strip()
                    block = (po.get("Block") or "").strip()
                    city = block if block and block.upper() != "NA" else ((po.get("Name") or district).strip())
                    
                    result = {
                        "pincode": p,
                        "state": state,
                        "district": district,
                        "city": city,
                        "post_offices": [o.get("Name") for o in first["PostOffice"] if o.get("Name")][:5],
                    }
                    _PINCODE_CACHE[p] = result
                    return result
    except Exception as e:
        logger.warning(f"Failed to lookup pincode {p}: {e}")

    return None
