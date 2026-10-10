from rest_framework import permissions, serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import User


class IsAdminOrHRForWrites(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.company_id:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in ("admin", "hr")


class EmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "password", "email", "first_name", "last_name",
            "role", "phone", "department", "designation", "date_of_joining",
            "manager", "manager_name", "is_active",
        ]

    def get_manager_name(self, obj):
        return (obj.manager.get_full_name() or obj.manager.username) if obj.manager else None

    def validate(self, attrs):
        me = self.context["request"].user
        if attrs.get("role") == "admin" and me.role != "admin":
            raise serializers.ValidationError({"role": "Only an admin can assign the admin role."})
        manager = attrs.get("manager")
        if manager and manager.company_id != me.company_id:
            raise serializers.ValidationError({"manager": "Manager must be in your company."})
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        company = self.context["request"].user.company
        return User.objects.create_user(password=password, company=company, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminOrHRForWrites]

    def get_queryset(self):
        return (
            User.objects.filter(company=self.request.user.company)
            .select_related("manager")
            .order_by("first_name", "username")
        )

    def perform_update(self, serializer):
        me = self.request.user
        target = serializer.instance
        if target.role == "admin" and me.role != "admin":
            raise PermissionDenied("Only an admin can edit an admin.")
        if target == me and serializer.validated_data.get("is_active") is False:
            raise PermissionDenied("You cannot deactivate yourself.")
        serializer.save()

    def perform_destroy(self, instance):
        me = self.request.user
        if instance == me:
            raise PermissionDenied("You cannot deactivate yourself.")
        if instance.role == "admin" and me.role != "admin":
            raise PermissionDenied("Only an admin can deactivate an admin.")
        instance.is_active = False
        instance.save()