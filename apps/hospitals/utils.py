import io
import os
import re

from PIL import Image, ImageEnhance
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile


def process_aadhaar_upload(uploaded_file: UploadedFile) -> dict:
    if not isinstance(uploaded_file, UploadedFile):
        raise TypeError("uploaded_file must be an UploadedFile")

    image = Image.open(uploaded_file).convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.2)
    image = ImageEnhance.Brightness(image).enhance(1.05)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    cleaned_text = ""
    try:
        import pytesseract

        text = pytesseract.image_to_string(image)
        cleaned_text = re.sub(r"\s+", " ", text).strip()
    except Exception:
        cleaned_text = ""

    return {
        "processed_file": SimpleUploadedFile(
            os.path.splitext(uploaded_file.name)[0] + "_processed.png",
            buffer.getvalue(),
            content_type="image/png",
        ),
        "ocr_text": cleaned_text,
    }
