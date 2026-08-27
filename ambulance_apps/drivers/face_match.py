def compare_faces(selfie_image, id_card_image):
    """
    Simulates verifying if the driver's uploaded selfie matches their ID card photo.
    Returns a similarity score decimal representing match confidence.
    In production, this would use the DeepFace / face_recognition packages.
    """
    if not selfie_image or not id_card_image:
        return 0.0
    return 0.93
