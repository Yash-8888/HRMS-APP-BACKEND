import calendar
from decimal import Decimal, InvalidOperation

from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Payslip, SalaryStructure
from .serializers import PayslipSerializer, SalarySerializer

HR_ROLES = ("admin", "hr")


class HRManagesPayroll(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u.is_authenticated and u.company_id):
            return False
        if getattr(view, "hr_only", False) or getattr(view, "action", None) in ("generate", "mark_paid", "destroy"):
            return u.role in HR_ROLES
        return True


class SalaryViewSet(viewsets.ModelViewSet):
    serializer_class = SalarySerializer
    permission_classes = [HRManagesPayroll]
    hr_only = True
    lookup_field = "employee_id"

    def get_queryset(self):
        return SalaryStructure.objects.filter(employee__company=self.request.user.company)


class PayslipViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = PayslipSerializer
    permission_classes = [HRManagesPayroll]

    def get_queryset(self):
        user = self.request.user
        qs = Payslip.objects.select_related("employee")
        if user.role in HR_ROLES and (
            self.action != "list" or self.request.query_params.get("scope") == "all"
        ):
            return qs.filter(employee__company=user.company)
        return qs.filter(employee=user)

    def perform_destroy(self, instance):
        if instance.status == Payslip.Status.PAID:
            raise ValidationError({"detail": "Paid payslips cannot be deleted."})
        instance.delete()

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        payslip = self.get_object()
        payslip.status = Payslip.Status.PAID
        payslip.save()
        return Response(self.get_serializer(payslip).data)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        try:
            month = int(request.data.get("month"))
            year = int(request.data.get("year"))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Month and year are required."})
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValidationError({"detail": "Invalid month or year."})

        lop = request.data.get("lop") or {}
        days_in_month = calendar.monthrange(year, month)[1]
        created, skipped = 0, 0

        structures = SalaryStructure.objects.filter(
            employee__company=request.user.company, employee__is_active=True
        ).select_related("employee")

        for s in structures:
            if Payslip.objects.filter(employee=s.employee, month=month, year=year).exists():
                skipped += 1
                continue
            try:
                lop_days = Decimal(str(lop.get(str(s.employee_id), 0) or 0))
            except InvalidOperation:
                raise ValidationError({"detail": f"Invalid LOP days for {s.employee.username}."})
            if not (0 <= lop_days <= days_in_month):
                raise ValidationError({"detail": f"LOP days out of range for {s.employee.username}."})

            gross = s.basic + s.hra + s.allowances
            lop_deduction = (gross / days_in_month * lop_days).quantize(Decimal("0.01"))
            total_deductions = s.pf_deduction + s.professional_tax + s.other_deductions + lop_deduction
            Payslip.objects.create(
                employee=s.employee, month=month, year=year,
                basic=s.basic, hra=s.hra, allowances=s.allowances, gross=gross,
                pf_deduction=s.pf_deduction, professional_tax=s.professional_tax,
                other_deductions=s.other_deductions, lop_days=lop_days,
                lop_deduction=lop_deduction, total_deductions=total_deductions,
                net_pay=gross - total_deductions,
            )
            created += 1

        return Response({"created": created, "skipped": skipped})