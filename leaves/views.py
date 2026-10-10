from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LeaveRequest
from .serializers import (
    LeaveRequestSerializer, LeaveTypeSerializer, booked_days, ensure_default_types,
)


class HasCompany(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and bool(request.user.company_id)


class LeaveTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasCompany]

    def get_queryset(self):
        company = self.request.user.company
        ensure_default_types(company)
        return company.leave_types.all()


class LeaveRequestViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasCompany]

    def _team(self, qs):
        user = self.request.user
        if user.role in ("admin", "hr"):
            return qs.filter(employee__company_id=user.company_id)
        if user.role == "manager":
            return qs.filter(employee__manager=user)
        return qs.none()

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee", "leave_type", "reviewed_by")
        wants_team = self.request.query_params.get("scope") == "team"
        if self.action in ("approve", "reject") or (self.action == "list" and wants_team):
            return self._team(qs)
        return qs.filter(employee=self.request.user)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)

    @action(detail=False, methods=["get"])
    def balance(self, request):
        user = request.user
        ensure_default_types(user.company)
        year = timezone.localdate().year
        data = []
        for lt in user.company.leave_types.all():
            used = booked_days(user, lt, year, ["approved"])
            pending = booked_days(user, lt, year, ["pending"])
            data.append({
                "id": lt.id, "name": lt.name, "quota": lt.annual_quota,
                "used": used, "pending": pending, "remaining": lt.annual_quota - used - pending,
            })
        return Response(data)

    def _review(self, request, new_status):
        leave = self.get_object()
        if leave.employee_id == request.user.id:
            return Response({"detail": "You cannot review your own request."}, status=403)
        if leave.status != LeaveRequest.Status.PENDING:
            return Response({"detail": "This request was already handled."}, status=400)
        leave.status = new_status
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.review_note = request.data.get("note", "")
        leave.save()
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._review(request, LeaveRequest.Status.APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._review(request, LeaveRequest.Status.REJECTED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        leave = self.get_object()
        if leave.status != LeaveRequest.Status.PENDING:
            return Response({"detail": "Only pending requests can be cancelled."}, status=400)
        leave.status = LeaveRequest.Status.CANCELLED
        leave.save()
        return Response(self.get_serializer(leave).data)