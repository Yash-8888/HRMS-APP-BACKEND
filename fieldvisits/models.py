from django.conf import settings
from django.db import models


class FieldVisit(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="field_visits")
    client_name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    purpose = models.TextField(blank=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]