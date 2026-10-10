from rest_framework import serializers

from .models import Payslip, SalaryStructure


class SalarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = "__all__"

    def validate_employee(self, value):
        if value.company_id != self.context["request"].user.company_id:
            raise serializers.ValidationError("Employee must be in your company.")
        return value

    def validate(self, attrs):
        for key, val in attrs.items():
            if key != "employee" and val < 0:
                raise serializers.ValidationError({key: "Cannot be negative."})
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("employee", None)
        return super().update(instance, validated_data)


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    designation = serializers.CharField(source="employee.designation", read_only=True)

    class Meta:
        model = Payslip
        fields = "__all__"

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username