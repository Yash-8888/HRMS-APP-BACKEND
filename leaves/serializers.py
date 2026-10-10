from django.db.models import Sum
from rest_framework import serializers

from .models import LeaveRequest, LeaveType

DEFAULT_TYPES = [("Casual Leave", 12), ("Sick Leave", 8), ("Earned Leave", 15)]


def ensure_default_types(company):
    if not company.leave_types.exists():
        LeaveType.objects.bulk_create(
            [LeaveType(company=company, name=n, annual_quota=q) for n, q in DEFAULT_TYPES]
        )


def booked_days(user, leave_type, year, statuses):
    total = LeaveRequest.objects.filter(
        employee=user, leave_type=leave_type, start_date__year=year, status__in=statuses
    ).aggregate(t=Sum("days"))["t"]
    return total or 0


def _name(u):
    return (u.get_full_name() or u.username) if u else None


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "name", "annual_quota"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "employee", "days", "status", "reviewed_by", "reviewed_at", "review_note", "created_at",
        ]

    def get_employee_name(self, obj):
        return _name(obj.employee)

    def get_reviewed_by_name(self, obj):
        return _name(obj.reviewed_by)

    def validate(self, attrs):
        user = self.context["request"].user
        lt, start, end = attrs["leave_type"], attrs["start_date"], attrs["end_date"]
        if lt.company_id != user.company_id:
            raise serializers.ValidationError({"leave_type": "Invalid leave type."})
        if end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        if start.year != end.year:
            raise serializers.ValidationError({"end_date": "Split leave across years into separate requests."})
        overlap = LeaveRequest.objects.filter(
            employee=user, status__in=["pending", "approved"], start_date__lte=end, end_date__gte=start
        ).exists()
        if overlap:
            raise serializers.ValidationError({"start_date": "You already have leave in these dates."})
        days = (end - start).days + 1
        remaining = lt.annual_quota - booked_days(user, lt, start.year, ["pending", "approved"])
        if days > remaining:
            raise serializers.ValidationError({"leave_type": f"Only {remaining} day(s) left for {lt.name}."})
        attrs["days"] = days
        return attrs