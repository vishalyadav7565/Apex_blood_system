from ambulance_apps.drivers.ocr import perform_aadhaar_ocr, perform_dl_ocr
from ambulance_apps.drivers.face_match import compare_faces


def verify_driver_documents(driver):
    """
    Orchestrates the Phase 4 validation pipeline:
    - Runs Aadhaar OCR
    - Runs Driving Licence OCR
    - Matches driver selfie against the ID cards
    Logs results directly on the Driver instance.
    """
    updated_fields = []

    # 1. Process Aadhaar Card
    if driver.aadhaar_card and not driver.aadhaar_ocr_data:
        ocr_result = perform_aadhaar_ocr(driver.aadhaar_card)
        driver.aadhaar_ocr_data = ocr_result
        if ocr_result.get('aadhaar_number'):
            driver.aadhaar_number = ocr_result['aadhaar_number']
            updated_fields.append('aadhaar_number')
        updated_fields.append('aadhaar_ocr_data')

    # 2. Process Driving Licence
    if driver.driving_licence and not driver.dl_ocr_data:
        ocr_result = perform_dl_ocr(driver.driving_licence)
        driver.dl_ocr_data = ocr_result
        if ocr_result.get('license_number'):
            driver.license_number = ocr_result['license_number']
            updated_fields.append('license_number')
        updated_fields.append('dl_ocr_data')

    # 3. Perform Face Matching
    if driver.photo and (driver.aadhaar_card or driver.driving_licence) and not driver.face_match_score:
        id_img = driver.aadhaar_card or driver.driving_licence
        match_score = compare_faces(driver.photo, id_img)
        driver.face_match_score = match_score
        updated_fields.append('face_match_score')

    # Save details
    if updated_fields:
        driver.save(update_fields=updated_fields)

    return {
        "success": True,
        "aadhaar_processed": bool(driver.aadhaar_ocr_data),
        "dl_processed": bool(driver.dl_ocr_data),
        "face_match_score": driver.face_match_score
    }
