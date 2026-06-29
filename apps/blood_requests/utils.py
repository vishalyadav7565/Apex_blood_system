from geopy.distance import geodesic
from apps.users.models import User
from apps.notifications.utils import send_push_notification

COMPATIBLE_DONORS = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"],
}

def notify_compatible_donors(req):
    compatible_groups = COMPATIBLE_DONORS.get(req.blood_group, [req.blood_group])
    
    donors = User.objects.filter(
        is_donor=True,
        is_available=True,
        blood_group__in=compatible_groups
    ).exclude(fcm_token__isnull=True).exclude(fcm_token="")

    count = 0
    for donor in donors:
        if donor.latitude and donor.longitude and donor.fcm_token:
            try:
                dist = geodesic(
                    (float(req.latitude), float(req.longitude)),
                    (float(donor.latitude), float(donor.longitude))
                ).km
                
                if dist <= 10:  # 10 km range for donors
                    success = send_push_notification(
                        token=donor.fcm_token,
                        title="Urgent: Blood Donor Needed!",
                        body=f"A patient near you needs {req.blood_group} blood. Distance: {round(dist, 1)} km.",
                        data={
                            "event": "DONOR_NEEDED",
                            "request_id": str(req.id),
                            "blood_group": str(req.blood_group)
                        }
                    )
                    if success:
                        count += 1
            except Exception as e:
                print(f"Error notifying donor {donor.id}: {e}")
                
    return count
