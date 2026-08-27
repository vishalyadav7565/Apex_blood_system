import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .utils import process_aadhaar_upload


class AadhaarUploadProcessingTests(TestCase):
    def test_process_aadhaar_upload_returns_processed_image(self):
        image = Image.new("RGB", (240, 140), color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        uploaded = SimpleUploadedFile(
            "aadhaar.png",
            buffer.getvalue(),
            content_type="image/png",
        )

        result = process_aadhaar_upload(uploaded)

        self.assertIn("processed_file", result)
        self.assertGreater(result["processed_file"].size, 0)
        self.assertEqual(result["processed_file"].content_type, "image/png")
