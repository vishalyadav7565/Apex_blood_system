from celery import shared_task
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from geopy.distance import geodesic
from apps.users.models import User
from .models import BloodRequest
from .utils import notify_compatible_donors, COMPATIBLE_DONORS

@shared_task
def fallback_requests():
    now = timezone.now()

    expired = BloodRequest.objects.filter(
        status__in=['pending', 'broadcasting', 'searching_hospital', 'searching_next_hospital'],
        expiry_time__lt=now
    )

    channel_layer = get_channel_layer()

    for req in expired:
        # Scan for compatible donors within 10 km
        compatible_groups = COMPATIBLE_DONORS.get(req.blood_group, [req.blood_group])
        donors = User.objects.filter(
            is_donor=True,
            is_available=True,
            blood_group__in=compatible_groups
        )
        nearby_donors = []
        for donor in donors:
            if donor.latitude and donor.longitude:
                dist = geodesic(
                    (float(req.latitude), float(req.longitude)),
                    (float(donor.latitude), float(donor.longitude))
                ).km
                if dist <= 10:
                    nearby_donors.append({
                        "id": donor.id,
                        "name": (f"{donor.first_name} {donor.last_name}").strip() or donor.username,
                        "distance": round(dist, 2),
                        "lat": donor.latitude,
                        "lng": donor.longitude,
                        "phone": donor.phone,
                        "blood_group": donor.blood_group
                    })

        req.status = 'searching_donor'
        req.save()
        notify_compatible_donors(req)

        # Webhook Admin Update
        async_to_sync(channel_layer.group_send)(
            "requests",
            {
                "type": "send_update",
                "data": {
                    "event": "SEARCHING_DONOR",
                    "request_id": req.id,
                    "status": req.status,
                    "blood_group": req.blood_group,
                }
            }
        )

        # Webhook User Update with nearby donors
        async_to_sync(channel_layer.group_send)(
            f"user_{req.user.id}",
            {
                "type": "send_update",
                "data": {
                    "event": "SEARCHING_DONOR",
                    "request_id": req.id,
                    "status": req.status,
                    "message": "Hospitals busy. Searching nearby blood donors...",
                    "nearby_donors": nearby_donors
                }
            }
        )

    return "done"