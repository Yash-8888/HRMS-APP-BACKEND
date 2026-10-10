from rest_framework import serializers

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    worked_hours = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "date", "check_in", "check_out", "worked_hours"]

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username

    def get_worked_hours(self, obj):
        if obj.check_in and obj.check_out:
            return round((obj.check_out - obj.check_in).total_seconds() / 3600, 2)
        return None