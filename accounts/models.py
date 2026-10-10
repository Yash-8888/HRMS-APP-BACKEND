from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLES = [
        ("admin", "Company Admin"),
        ("hr", "HR"),
        ("manager", "Manager"),
        ("employee", "Employee"),
    ]
    company = models.ForeignKey(
        "companies.Company", null=True, on_delete=models.CASCADE, related_name="users"
    )
    role = models.CharField(max_length=20, choices=ROLES, default="employee")
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )