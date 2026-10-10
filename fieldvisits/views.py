from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import FieldVisit
from .serializers import FieldVisitSerializer


class FieldVisitViewSet(viewsets.ModelViewSet):
    serializer_class = FieldVisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = FieldVisit.objects.select_related("employee")
        wants_team = self.request.query_params.get("scope") == "team"
        if (
            self.action == "list"
            and wants_team
            and user.role in ("admin", "hr", "manager")
            and user.company_id
        ):
            return qs.filter(employee__company_id=user.company_id)
        return qs.filter(employee=user)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        visit = self.get_object()
        if visit.status != FieldVisit.Status.PLANNED:
            return Response({"detail": "Visit already started."}, status=400)
        visit.status = FieldVisit.Status.IN_PROGRESS
        visit.check_in_at = timezone.now()
        visit.save()
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        visit = self.get_object()
        if visit.status != FieldVisit.Status.IN_PROGRESS:
            return Response({"detail": "Check in first."}, status=400)
        visit.status = FieldVisit.Status.COMPLETED
        visit.check_out_at = timezone.now()
        visit.notes = request.data.get("notes", visit.notes)
        visit.save()
        return Response(self.get_serializer(visit).data)