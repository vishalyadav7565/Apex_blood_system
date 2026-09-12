from rest_framework.test import APITestCase

from ambulance_apps.ambulance.models import Ambulance
from ambulance_apps.drivers.models import Driver
from ambulance_apps.owners.models import Owner
from ambulance_apps.trips.models import Trip


class CreateBookingTests(APITestCase):
    databases = {'ambulance_db'}

    def setUp(self):
        owner = Owner.objects.create(
            name='Booking Owner',
            phone='9000000001',
            email='booking-owner@example.com',
            password='password',
        )
        self.ambulance = Ambulance.objects.create(
            vehicle_number='BOOK-101',
            registration_number='BOOK-REG-101',
            ambulance_type='BLS',
            owner=owner,
            is_active=True,
            is_approved=True,
            is_available=True,
            status='online',
        )
        self.driver = Driver.objects.create(
            name='Booking Driver',
            phone='9000000002',
            email='booking-driver@example.com',
            password='password',
            license_number='BOOK-DL-101',
            ambulance=self.ambulance,
            is_verified=True,
            is_online=True,
            current_latitude=19.0760,
            current_longitude=72.8777,
        )

    def test_create_booking_reserves_ambulance(self):
        response = self.client.post(
            '/api/ambulance/bookings/',
            {
                'driver_id': self.driver.id,
                'patient_name': 'Jane Patient',
                'patient_phone': '9000000003',
                'pickup_address': '12 Pickup Road',
                'destination_address': 'City Hospital',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Trip.objects.count(), 1)
        self.ambulance.refresh_from_db()
        self.assertFalse(self.ambulance.is_available)
        self.assertEqual(self.ambulance.status, 'busy')

    def test_create_booking_rejects_unavailable_ambulance(self):
        self.ambulance.is_available = False
        self.ambulance.status = 'busy'
        self.ambulance.save()

        response = self.client.post(
            '/api/ambulance/bookings/',
            {
                'driver_id': self.driver.id,
                'patient_name': 'Jane Patient',
                'pickup_address': '12 Pickup Road',
                'destination_address': 'City Hospital',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Trip.objects.count(), 0)

    def test_create_booking_by_ambulance_type(self):
        response = self.client.post(
            '/api/ambulance/bookings/',
            {
                'ambulance_type': 'BLS',
                'patient_name': 'Type Booking Patient',
                'pickup_address': '12 Pickup Road',
                'destination_address': 'City Hospital',
                'pickup_latitude': 19.0800,
                'pickup_longitude': 72.8800,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['trip']['ambulance_type'], 'BLS')
        self.assertEqual(response.data['trip']['driver'], self.driver.id)
        self.assertEqual(response.data['trip']['driver_details']['name'], self.driver.name)
        self.assertLessEqual(response.data['driver_distance_km'], 20)

    def test_booking_history_splits_live_and_past_bookings(self):
        live_trip = Trip.objects.create(
            driver=self.driver,
            ambulance_type='BLS',
            patient_phone='9000000003',
            patient_name='Live Patient',
            pickup_address='Pickup',
            destination_address='Destination',
            status='started',
        )
        Trip.objects.create(
            driver=self.driver,
            ambulance_type='BLS',
            patient_phone='9000000003',
            patient_name='Past Patient',
            pickup_address='Pickup',
            destination_address='Destination',
            status='completed',
        )

        response = self.client.get('/api/ambulance/bookings/history/?patient_phone=9000000003')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['live_count'], 1)
        self.assertEqual(response.data['past_count'], 1)
        self.assertEqual(response.data['live_bookings'][0]['id'], live_trip.id)

    def test_nearby_options_returns_two_closest_drivers_within_five_km(self):
        second_ambulance = Ambulance.objects.create(
            vehicle_number='BOOK-102',
            registration_number='BOOK-REG-102',
            ambulance_type='BLS',
            is_active=True,
            is_approved=True,
            is_available=True,
            status='online',
        )
        Driver.objects.create(
            name='Second Booking Driver',
            phone='9000000004',
            password='password',
            license_number='BOOK-DL-102',
            ambulance=second_ambulance,
            is_verified=True,
            is_online=True,
            current_latitude=19.0850,
            current_longitude=72.8820,
        )

        response = self.client.get(
            '/api/ambulance/bookings/nearby/'
            '?ambulance_type=BLS&pickup_latitude=19.0800&pickup_longitude=72.8800'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['options']), 2)
        self.assertEqual(response.data['options'][0]['driver_id'], self.driver.id)
        self.assertLessEqual(response.data['options'][0]['driver_distance_km'], 5)

    def test_driver_can_accept_a_requested_booking(self):
        trip = Trip.objects.create(
            driver=self.driver,
            ambulance_type='BLS',
            patient_name='Waiting Patient',
            pickup_address='Pickup',
            destination_address='Destination',
            status='requested',
        )

        response = self.client.post(
            f'/api/ambulance/bookings/{trip.id}/accept/',
            {'driver_id': self.driver.id},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'accepted')
        self.assertIsNotNone(trip.accepted_at)

    def test_driver_rejection_releases_ambulance(self):
        trip = Trip.objects.create(
            driver=self.driver,
            ambulance_type='BLS',
            patient_name='Waiting Patient',
            pickup_address='Pickup',
            destination_address='Destination',
            status='requested',
        )
        self.ambulance.is_available = False
        self.ambulance.status = 'busy'
        self.ambulance.save()

        response = self.client.post(
            f'/api/ambulance/bookings/{trip.id}/reject/',
            {'driver_id': self.driver.id, 'reason': 'Vehicle needs fuel'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        trip.refresh_from_db()
        self.ambulance.refresh_from_db()
        self.assertEqual(trip.status, 'rejected')
        self.assertTrue(self.ambulance.is_available)

    def test_user_can_book_the_exact_selected_ambulance(self):
        response = self.client.post(
            '/api/ambulance/bookings/',
            {
                'ambulance_id': self.ambulance.id,
                'ambulance_type': 'BLS',
                'patient_name': 'Selected Ambulance Patient',
                'pickup_address': 'Pickup',
                'destination_address': 'Destination',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['trip']['driver'], self.driver.id)
        self.ambulance.refresh_from_db()
        self.assertEqual(self.ambulance.status, 'busy')

    def test_selected_ambulance_must_match_requested_type(self):
        response = self.client.post(
            '/api/ambulance/bookings/',
            {
                'ambulance_id': self.ambulance.id,
                'ambulance_type': 'ICU',
                'patient_name': 'Selected Ambulance Patient',
                'pickup_address': 'Pickup',
                'destination_address': 'Destination',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Trip.objects.count(), 0)
