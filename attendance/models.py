from django.conf import settings
from django.db import models


class Attendance(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date"]