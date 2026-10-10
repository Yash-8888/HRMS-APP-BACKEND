from django.contrib.auth import get_user_model
from rest_framework import serializers
from companies.models import Company

User = get_user_model()


class CompanySignupSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=200)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken")
        return value

    def create(self, data):
        company = Company.objects.create(name=data["company_name"])
        return User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            company=company,
            role="admin",
        )


class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "company", "company_name"]