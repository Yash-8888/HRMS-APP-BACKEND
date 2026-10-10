from django.conf import settings
from django.db import models

money = dict(max_digits=10, decimal_places=2, default=0)


class SalaryStructure(models.Model):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salary")
    basic = models.DecimalField(**money)
    hra = models.DecimalField(**money)
    allowances = models.DecimalField(**money)
    pf_deduction = models.DecimalField(**money)
    professional_tax = models.DecimalField(**money)
    other_deductions = models.DecimalField(**money)


class Payslip(models.Model):
    class Status(models.TextChoices):
        GENERATED = "generated"
        PAID = "paid"

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payslips")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    basic = models.DecimalField(**money)
    hra = models.DecimalField(**money)
    allowances = models.DecimalField(**money)
    gross = models.DecimalField(**money)
    pf_deduction = models.DecimalField(**money)
    professional_tax = models.DecimalField(**money)
    other_deductions = models.DecimalField(**money)
    lop_days = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    lop_deduction = models.DecimalField(**money)
    total_deductions = models.DecimalField(**money)
    net_pay = models.DecimalField(**money)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("employee", "month", "year")
        ordering = ["-year", "-month", "employee__first_name"]