from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ("id", "email", "password", "display_name")
        read_only_fields = ("id",)

    def create(self, validated_data):
        email = validated_data["email"]
        return User.objects.create_user(
            email=email,
            password=validated_data["password"],
            display_name=validated_data.get("display_name", ""),
        )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "display_name", "role")
