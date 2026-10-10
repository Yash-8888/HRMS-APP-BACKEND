from django.conf import settings
from django.db import models


class LeaveType(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="leave_types")
    name = models.CharField(max_length=60)
    annual_quota = models.PositiveIntegerField(default=12)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        CANCELLED = "cancelled"

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]