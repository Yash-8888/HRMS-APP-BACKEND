import calendar
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from leaves.models import LeaveRequest

from .models import Attendance
from .serializers import AttendanceSerializer

HR_ROLES = ("admin", "hr")
WEEKEND_DAYS = (5, 6)  # Saturday, Sunday


class HasCompany(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and bool(request.user.company_id)


def _period(request):
    today = timezone.localdate()
    try:
        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))
        start = date(year, month, 1)
    except (TypeError, ValueError):
        raise ValidationError({"detail": "Invalid month or year."})
    return start, date(year, month, calendar.monthrange(year, month)[1])


class AttendanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [HasCompany]

    def _team(self, qs):
        user = self.request.user
        if user.role in HR_ROLES:
            return qs.filter(employee__company_id=user.company_id)
        if user.role == "manager":
            return qs.filter(employee__manager=user)
        return qs.none()

    def get_queryset(self):
        qs = Attendance.objects.select_related("employee")
        if self.request.query_params.get("scope") == "team":
            qs = self._team(qs)
        else:
            qs = qs.filter(employee=self.request.user)
        start, end = _period(self.request)
        return qs.filter(date__range=(start, end))

    @action(detail=False, methods=["get"])
    def today(self, request):
        rec = Attendance.objects.filter(employee=request.user, date=timezone.localdate()).first()
        return Response(self.get_serializer(rec).data if rec else None)

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        rec, created = Attendance.objects.get_or_create(
            employee=request.user, date=timezone.localdate(), defaults={"check_in": timezone.now()}
        )
        if not created:
            raise ValidationError({"detail": "Already checked in today."})
        return Response(self.get_serializer(rec).data, status=201)

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        rec = Attendance.objects.filter(employee=request.user, date=timezone.localdate()).first()
        if not rec or not rec.check_in:
            raise ValidationError({"detail": "Check in first."})
        if rec.check_out:
            raise ValidationError({"detail": "Already checked out today."})
        rec.check_out = timezone.now()
        rec.save()
        return Response(self.get_serializer(rec).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        user = request.user
        if user.role not in HR_ROLES:
            raise PermissionDenied("Only admin or HR can view the summary.")

        start, end = _period(request)
        last = min(end, timezone.localdate())
        if last < start:
            return Response([])

        days = [start + timedelta(d) for d in range((last - start).days + 1)]
        workdays = [d for d in days if d.weekday() not in WEEKEND_DAYS]

        present_map = {}
        rows = Attendance.objects.filter(
            employee__company=user.company, date__range=(start, last), check_in__isnull=False
        ).values_list("employee_id", "date")
        for emp_id, d in rows:
            present_map.setdefault(emp_id, set()).add(d)

        leave_map = {}
        leaves = LeaveRequest.objects.filter(
            employee__company=user.company, status="approved", start_date__lte=last, end_date__gte=start
        )
        for lv in leaves:
            cur, stop = max(lv.start_date, start), min(lv.end_date, last)
            while cur <= stop:
                leave_map.setdefault(lv.employee_id, set()).add(cur)
                cur += timedelta(days=1)

        result = []
        employees = get_user_model().objects.filter(company=user.company, is_active=True)
        for e in employees.order_by("first_name", "username"):
            wd = {d for d in workdays if not e.date_of_joining or d >= e.date_of_joining}
            present_days = present_map.get(e.id, set())
            present = len(present_days & wd)
            on_leave = len((leave_map.get(e.id, set()) & wd) - present_days)
            result.append({
                "id": e.id,
                "name": e.get_full_name() or e.username,
                "working_days": len(wd),
                "present": present,
                "on_leave": on_leave,
                "absent": len(wd) - present - on_leave,
            })
        return Response(result)