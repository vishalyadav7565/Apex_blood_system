from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APITestCase

from ambulance_apps.drivers.models import Driver
from ambulance_apps.ambulance.models import Ambulance
from apps.hospitals.models import Hospital


class PincodeLookupTests(TestCase):
    databases = '__all__'
    def test_known_pincode(self):
        response = self.client.get('/api/ambulance/drivers/pincode-lookup/?pincode=400018')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['district'], 'Mumbai')
        self.assertEqual(response.json()['state'], 'Maharashtra')

    def test_fallback_pincode(self):
        response = self.client.get('/api/ambulance/drivers/pincode-lookup/?pincode=500231')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['district'], 'Southern District')
        self.assertEqual(response.json()['state'], 'Telangana/Andhra Pradesh/Karnataka')


class DriverAPITests(APITestCase):
    databases = '__all__'
    def setUp(self):
        self.hospital = Hospital.objects.create(
            name="Apex General Hospital",
            email="owner@example.com",
            password="secure-password"
        )
        self.ambulance = Ambulance.objects.create(
            vehicle_number="MH-12-AB-9999",
            ambulance_type="ALS",
            registration_number="REG-777",
            hospital=self.hospital,
        )

    def test_register_driver(self):
        response = self.client.post(
            '/api/ambulance/drivers/register-driver/',
            {
                "name": "Suresh Raina",
                "phone": "9998887776",
                "password": "driver-secure"
            },
            format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Driver.objects.filter(phone="9998887776").exists())

    @patch("ambulance_apps.drivers.views.send_mail")
    def test_link_ambulance(self, mock_send_mail):
        driver = Driver.objects.create(
            name="Mahendra Singh",
            phone="9898989898",
            password="secure"
        )
        response = self.client.post(
            '/api/ambulance/drivers/link-ambulance/',
            {
                "driver_id": driver.id,
                "ambulance_number": self.ambulance.vehicle_number
            },
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.ambulance, self.ambulance)
        self.assertEqual(driver.verification_status, "pending_owner_review")
        self.assertEqual(mock_send_mail.call_count, 1)

    def test_document_upload_triggers_ocr(self):
        driver = Driver.objects.create(
            name="Virat Kohli",
            phone="9797979797",
            password="secure"
        )
        
        # Mock file uploads
        from django.core.files.uploadedfile import SimpleUploadedFile
        dummy_pic = SimpleUploadedFile("selfie.jpg", b"file_content", content_type="image/jpeg")
        dummy_aadhaar = SimpleUploadedFile("aadhaar.jpg", b"file_content", content_type="image/jpeg")
        
        response = self.client.post(
            '/api/ambulance/drivers/upload-doc/',
            {
                "driver_id": driver.id,
                "photo": dummy_pic,
                "aadhaar_card": dummy_aadhaar
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 200)
        driver.refresh_from_db()
        
        # Verify simulated OCR & face match results populated
        self.assertIsNotNone(driver.aadhaar_ocr_data)
        self.assertEqual(driver.aadhaar_number, "123456789012")
        self.assertEqual(driver.face_match_score, 0.93)
