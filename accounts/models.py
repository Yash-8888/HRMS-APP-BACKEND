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