from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountProfile, UserRole


User = get_user_model()


class AccountProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountProfile
        fields = ("role", "phone", "is_active_member")
        read_only_fields = ("role", "is_active_member")


class UserProfileSerializer(serializers.ModelSerializer):
    profile = AccountProfileSerializer(source="account_profile", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "profile")


class UserSummarySerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="account_profile.role", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=UserRole.choices, required=False, default=UserRole.AGENT)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password", "role")

    def create(self, validated_data):
        role = validated_data.pop("role", UserRole.AGENT)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        profile = user.account_profile
        profile.role = role
        profile.save(update_fields=["role", "updated_at"])
        return user


class LoginTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        role = getattr(user, "account_profile", None)
        token["role"] = role.role if role else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserProfileSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self):
        token = RefreshToken(self.token)
        token.blacklist()


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices)

    def validate_role(self, value):
        request = self.context["request"]
        if request.user.id == self.context["target_user"].id and value != UserRole.ADMIN:
            raise serializers.ValidationError(
                "Un administrateur ne peut pas se retirer son role ADMIN."
            )
        return value


class MyPermissionsSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices)
    permissions = serializers.DictField(
        child=serializers.BooleanField(),
    )
