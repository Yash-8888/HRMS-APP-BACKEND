from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        return bool(self.current_period_end and self.current_period_end > timezone.now())


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created"
        PAID = "paid"

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="payments")
    plan = models.CharField(max_length=20)
    amount = models.PositiveIntegerField(help_text="in paise")
    razorpay_order_id = models.CharField(max_length=64, unique=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)