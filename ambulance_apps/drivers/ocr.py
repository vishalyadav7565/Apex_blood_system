def perform_aadhaar_ocr(image):
    """
    Simulates extracting key text parameters from an Aadhaar card image.
    In production, this would initialize an EasyOCR/Tesseract engine.
    """
    return {
        "aadhaar_number": "123456789012",
        "name": "Amit Kumar Sharma",
        "dob": "1992-05-15",
        "gender": "Male",
        "ocr_confidence": 0.95
    }


def perform_dl_ocr(image):
    """
    Simulates extracting key text parameters from a Driving Licence image.
    """
    return {
        "license_number": "DL-1234567890",
        "name": "Amit Kumar Sharma",
        "expiry_date": "2036-05-15",
        "class_of_vehicle": "MCWG / LMV",
        "ocr_confidence": 0.92
    }
