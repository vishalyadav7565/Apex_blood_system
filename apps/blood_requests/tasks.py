from celery import shared_task
from django.utils import timezone
from .models import BloodRequest
from .utils import notify_compatible_donors

@shared_task
def fallback_requests():
    now = timezone.now()

    expired = BloodRequest.objects.filter(
        status='pending',
        expiry_time__lt=now
    )

    for req in expired:
        req.status = 'searching_donor'
        req.save()
        notify_compatible_donors(req)

    return "done"