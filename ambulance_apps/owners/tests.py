from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta

from apps.users.models import OTP
from ambulance_apps.owners.models import Owner, EmailOTP


class OwnerPipelineTests(APITestCase):
    databases = '__all__'
    def setUp(self):
        # Create a sample owner that will undergo verification/login tests
        self.owner_details = {
            "name": "Test Owner",
            "email": "owner@test.com",
            "phone": "9876543210",
            "password": "ownerpassword123",
            "company_name": "Apex Test Corp",
            "address": "456 Test Blvd"
        }

    def test_registration_initiates_otps(self):
        url = reverse('register-owner')
        response = self.client.post(url, self.owner_details, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("owner_id", response.data)
        self.assertIn("dev_email_otp", response.data)

        # Check DB
        owner = Owner.objects.get(email="owner@test.com")
        self.assertEqual(owner.verification_status, "pending_verification")
        self.assertFalse(owner.is_email_verified)
        self.assertFalse(owner.is_phone_verified)

    def test_verify_otps_success(self):
        # 1. Register to create record and generate OTPs
        self.client.post(reverse('register-owner'), self.owner_details, format='json')
        
        # Get OTPs from DB
        email_otp = EmailOTP.objects.filter(email="owner@test.com").latest('created_at').otp

        # 2. Verify OTPs
        url = reverse('verify-registration-otps')
        data = {
            "email": "owner@test.com",
            "email_otp": email_otp,
            "phone": "9876543210",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        owner = Owner.objects.get(email="owner@test.com")
        self.assertTrue(owner.is_email_verified)
        self.assertTrue(owner.is_phone_verified)

    def test_verify_otps_invalid(self):
        self.client.post(reverse('register-owner'), self.owner_details, format='json')
        
        url = reverse('verify-registration-otps')
        data = {
            "email": "owner@test.com",
            "email_otp": "000000",  # invalid
            "phone": "9876543210",
            "mobile_otp": "000000"  # invalid
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_digilocker_success(self):
        # Setup pre-verified OTPs
        owner = Owner.objects.create(
            name="Apex Owner",
            email="owner@test.com",
            phone="9876543210",
            password="password",
            is_email_verified=True,
            is_phone_verified=True
        )

        url = reverse('verify-digilocker')
        data = {
            "owner_id": owner.id,
            "digilocker_code": "dl_auth_code_12345"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        owner.refresh_from_db()
        self.assertTrue(owner.is_aadhaar_verified)
        self.assertEqual(owner.aadhaar_number, "5432-1098-7654")
        self.assertIsNotNone(owner.digilocker_token)

    def test_verify_digilocker_pre_requisite_fail(self):
        owner = Owner.objects.create(
            name="Apex Owner",
            email="owner@test.com",
            phone="9876543210",
            password="password",
            is_email_verified=False,  # not verified
            is_phone_verified=False
        )

        url = reverse('verify-digilocker')
        data = {
            "owner_id": owner.id,
            "digilocker_code": "dl_auth_code_12345"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_documents_success(self):
        owner = Owner.objects.create(
            name="Apex Owner",
            email="owner@test.com",
            phone="9876543210",
            password="password",
            is_email_verified=True,
            is_phone_verified=True,
            is_aadhaar_verified=True
        )

        dummy_doc = SimpleUploadedFile("business_doc.pdf", b"file_content", content_type="application/pdf")
        dummy_selfie = SimpleUploadedFile("selfie.jpg", b"file_content", content_type="image/jpeg")

        url = reverse('upload-business-documents')
        data = {
            "owner_id": owner.id,
            "business_doc": dummy_doc,
            "selfie": dummy_selfie
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        owner.refresh_from_db()
        self.assertEqual(owner.verification_status, "pending_admin_review")
        self.assertEqual(owner.face_match_score, 0.98)
        self.assertIsNotNone(owner.business_doc)
        self.assertIsNotNone(owner.selfie)

    def test_login_request_and_verify(self):
        # Create an approved owner
        owner = Owner.objects.create(
            name="Approved Owner",
            email="approved@test.com",
            phone="9876543211",
            password="securepassword",
            verification_status="approved",
            is_verified=True
        )

        # 1. Direct Email + Password Login Request
        url_login_req = reverse('login-owner-request')
        data_login_req = {
            "email": "approved@test.com",
            "password": "securepassword"
        }
        response_req = self.client.post(url_login_req, data_login_req, format='json')
        self.assertEqual(response_req.status_code, status.HTTP_200_OK)
        self.assertIn("token", response_req.data)
        self.assertEqual(response_req.data['owner']['email'], "approved@test.com")

    def test_login_unapproved_owner(self):
        # Create a pending owner
        Owner.objects.create(
            name="Pending Owner",
            email="pending@test.com",
            phone="9876543212",
            password="securepassword",
            verification_status="pending_admin_review"
        )

        url = reverse('login-owner-request')
        data = {
            "email": "pending@test.com",
            "password": "securepassword"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('ambulance_apps.owners.views.verify_firebase_token')
    def test_verify_firebase_email_otp_success(self, mock_verify):
        # Setup mock decoded token
        mock_verify.return_value = {
            "email": "owner@test.com",
            "email_verified": True
        }

        owner = Owner.objects.create(
            name="Apex Owner",
            email="owner@test.com",
            phone="9876543210",
            password="password",
            is_email_verified=False
        )

        url = reverse('verify-firebase-email')
        data = {
            "email": "owner@test.com",
            "id_token": "mock-firebase-token-123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        owner.refresh_from_db()
        self.assertTrue(owner.is_email_verified)

    @patch('ambulance_apps.owners.views.verify_firebase_token')
    def test_login_owner_firebase_success(self, mock_verify):
        # Setup mock decoded token
        mock_verify.return_value = {
            "email": "approved@test.com",
            "email_verified": True
        }

        Owner.objects.create(
            name="Approved Owner",
            email="approved@test.com",
            phone="9876543211",
            password="securepassword",
            verification_status="approved",
            is_verified=True
        )

        url = reverse('login-owner-firebase')
        data = {
            "id_token": "mock-firebase-token-123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], "mock-jwt-token-owner-xyz")
        self.assertEqual(response.data['owner']['email'], "approved@test.com")

    @patch('ambulance_apps.owners.views.verify_firebase_token')
    def test_login_owner_firebase_from_existing_flutter_user(self, mock_verify):
        # Setup mock decoded token
        mock_verify.return_value = {
            "email": "flutter_user@test.com",
            "email_verified": True
        }

        # Create Flutter User
        from apps.users.models import User as FlutterUser
        FlutterUser.objects.create(
            username="flutter_user",
            email="flutter_user@test.com",
            phone="9876543219",
            first_name="Flutter",
            last_name="User"
        )

        url = reverse('login-owner-firebase')
        data = {
            "id_token": "mock-firebase-token-123"
        }
        # Check Owner table is empty for this email
        self.assertFalse(Owner.objects.filter(email="flutter_user@test.com").exists())

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Owner is created automatically
        self.assertTrue(Owner.objects.filter(email="flutter_user@test.com").exists())
        owner = Owner.objects.get(email="flutter_user@test.com")
        self.assertEqual(owner.name, "Flutter User")
        self.assertEqual(owner.phone, "9876543219")
        self.assertEqual(owner.verification_status, "approved")


