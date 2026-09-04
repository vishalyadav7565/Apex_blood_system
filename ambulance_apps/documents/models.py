from django.db import models

class VerificationSession(models.Model):
    """
    Model for real-time mobile/desktop document verification sessions
    """
    code = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=64, default='CREATED')
    front_image = models.TextField(blank=True, null=True)
    back_image = models.TextField(blank=True, null=True)
    selfie_image = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'verification_session'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.code} ({self.status})"

