from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from ambulance_apps.owners.models import Owner
from ambulance_apps.ambulance.models import Ambulance


class AmbulanceAPITestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(
            name="Apex General Hospital",
            email="apex@hospital.com",
            phone="9876543210",
            address="123 Health Ave",
            pincode="400001"
        )
        self.owner = Owner.objects.create(
            name="Rajesh Sharma",
            email="rajesh@ambulancefleet.com",
            phone="9876500112",
            company_name="Sharma Emergency Services"
        )

    def test_register_ambulance_success_with_owner(self):
        payload = {
            "vehicle_number": "MH-01-AB-8008",
            "ambulance_type": "ALS",
            "registration_number": "REG-MH-8008",
            "owner_id": self.owner.id,
            "status": "online"
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ambulance']['owner']['id'], self.owner.id)

        amb = Ambulance.objects.get(vehicle_number="MH-01-AB-8008")
        self.assertEqual(amb.owner, self.owner)
        self.assertEqual(amb.status, "online")

    def test_register_ambulance_invalid_owner_id(self):
        payload = {
            "vehicle_number": "MH-01-AB-8009",
            "ambulance_type": "BLS",
            "registration_number": "REG-MH-8009",
            "owner_id": 99999
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('owner_id', response.data)

    def test_register_ambulance_success_without_hospital_or_owner(self):
        payload = {
            "vehicle_number": "MH-01-AB-1001",
            "ambulance_type": "BLS",
            "registration_number": "REG-MH-1001",
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('ambulance', response.data)
        self.assertEqual(response.data['ambulance']['vehicle_number'], "MH-01-AB-1001")
        self.assertEqual(response.data['ambulance']['ambulance_type'], "BLS")

        # Verify database record
        amb = Ambulance.objects.get(vehicle_number="MH-01-AB-1001")
        self.assertIsNone(amb.hospital)
        self.assertIsNone(amb.owner)
        self.assertTrue(amb.is_active)
        self.assertTrue(amb.is_available)
        self.assertEqual(amb.status, "offline")

    def test_register_ambulance_success_with_hospital(self):
        payload = {
            "vehicle_number": "MH-01-AB-2002",
            "ambulance_type": "ALS",
            "registration_number": "REG-MH-2002",
            "hospital_id": self.hospital.id,
            "status": "online"
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ambulance']['hospital']['id'], self.hospital.id)

        amb = Ambulance.objects.get(vehicle_number="MH-01-AB-2002")
        self.assertEqual(amb.hospital, self.hospital)
        self.assertEqual(amb.status, "online")

    def test_register_ambulance_duplicate_vehicle_number(self):
        Ambulance.objects.create(
            vehicle_number="MH-01-AB-3003",
            ambulance_type="ICU",
            registration_number="REG-MH-3003"
        )
        payload = {
            "vehicle_number": "MH-01-AB-3003",
            "ambulance_type": "BLS",
            "registration_number": "REG-MH-9999",
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vehicle_number', response.data)

    def test_register_ambulance_duplicate_registration_number(self):
        Ambulance.objects.create(
            vehicle_number="MH-01-AB-4004",
            ambulance_type="ICU",
            registration_number="REG-MH-4004"
        )
        payload = {
            "vehicle_number": "MH-01-AB-9999",
            "ambulance_type": "BLS",
            "registration_number": "REG-MH-4004",
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registration_number', response.data)

    def test_register_ambulance_invalid_hospital_id(self):
        payload = {
            "vehicle_number": "MH-01-AB-5005",
            "ambulance_type": "Neonatal",
            "registration_number": "REG-MH-5005",
            "hospital_id": 99999
        }
        response = self.client.post('/api/ambulance/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hospital_id', response.data)

    def test_list_ambulances_and_filters(self):
        Ambulance.objects.create(
            vehicle_number="MH-01-AB-6001",
            ambulance_type="BLS",
            registration_number="REG-MH-6001",
            owner=self.owner,
            status="online",
            is_available=True
        )
        Ambulance.objects.create(
            vehicle_number="MH-01-AB-6002",
            ambulance_type="ALS",
            registration_number="REG-MH-6002",
            status="offline",
            is_available=False
        )

        # List all
        response = self.client.get('/api/ambulance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Filter by owner_id
        response = self.client.get(f'/api/ambulance/?owner_id={self.owner.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_number'], "MH-01-AB-6001")

        # Filter by status
        response = self.client.get('/api/ambulance/?status=online')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_number'], "MH-01-AB-6001")

        # Filter by type
        response = self.client.get('/api/ambulance/?ambulance_type=ALS')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_number'], "MH-01-AB-6002")

        # Search filter
        response = self.client.get('/api/ambulance/?search=6001')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_number'], "MH-01-AB-6001")

    def test_ambulance_detail_operations(self):
        amb = Ambulance.objects.create(
            vehicle_number="MH-01-AB-7007",
            ambulance_type="Patient Transport",
            registration_number="REG-MH-7007"
        )

        # GET detail
        response = self.client.get(f'/api/ambulance/{amb.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vehicle_number'], "MH-01-AB-7007")

        # PATCH detail
        response = self.client.patch(f'/api/ambulance/{amb.id}/', {"status": "busy"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amb.refresh_from_db()
        self.assertEqual(amb.status, "busy")

        # DELETE detail
        response = self.client.delete(f'/api/ambulance/{amb.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ambulance.objects.filter(id=amb.id).exists())
