from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.employees import EmployeeViewSet
from fieldvisits.views import FieldVisitViewSet
from leaves.views import LeaveRequestViewSet, LeaveTypeViewSet
from payroll.views import PayslipViewSet, SalaryViewSet
from attendance.views import AttendanceViewSet
from billing import views as billing_views

router = DefaultRouter()
router.register("field-visits", FieldVisitViewSet, basename="field-visit")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("leaves", LeaveRequestViewSet, basename="leave")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("salary", SalaryViewSet, basename="salary")
router.register("payslips", PayslipViewSet, basename="payslip")
router.register("attendance", AttendanceViewSet, basename="attendance")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/billing/subscription/", billing_views.subscription),
    path("api/billing/create-order/", billing_views.create_order),
    path("api/billing/verify/", billing_views.verify),
    path("api/billing/webhook/", billing_views.webhook),
    path("api/", include(router.urls)),
    path("api/auth/", include("accounts.urls")),
    path("api/auth/login/", TokenObtainPairView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
]