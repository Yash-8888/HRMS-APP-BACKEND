from rest_framework import serializers
from .models import FieldVisit


class FieldVisitSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.username", read_only=True)

    class Meta:
        model = FieldVisit
        fields = "__all__"
        read_only_fields = ["employee", "status", "check_in_at", "check_out_at", "created_at"]