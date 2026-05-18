from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import UserRole
from apps.accounts.serializers import (
    LoginTokenSerializer,
    LogoutSerializer,
    MyPermissionsSerializer,
    RegisterSerializer,
    UserRoleUpdateSerializer,
    UserProfileSerializer,
    UserSummarySerializer,
)
from core.api.permissions import IsAdminOrManagerRole, IsAdminRole, get_user_role


User = get_user_model()


class RegisterView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginTokenSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        disallowed_fields = {"profile", "role", "is_staff", "is_superuser", "password"}
        if disallowed_fields.intersection(set(request.data.keys())):
            return Response(
                {"detail": "Modification de champs sensibles non autorisee."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().patch(request, *args, **kwargs)


class UserListView(GenericAPIView):
    permission_classes = [IsAdminOrManagerRole]
    serializer_class = UserSummarySerializer

    def get(self, request):
        queryset = User.objects.select_related("account_profile").order_by("id")
        data = self.get_serializer(queryset, many=True).data
        return Response(data)


class UserRoleUpdateView(GenericAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = UserRoleUpdateSerializer

    def patch(self, request, user_id):
        target_user = get_object_or_404(User.objects.select_related("account_profile"), id=user_id)
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "target_user": target_user},
        )
        serializer.is_valid(raise_exception=True)

        target_user.account_profile.role = serializer.validated_data["role"]
        target_user.account_profile.save(update_fields=["role", "updated_at"])

        return Response(UserSummarySerializer(target_user).data, status=status.HTTP_200_OK)


class MyPermissionsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyPermissionsSerializer

    def get(self, request):
        role = get_user_role(request.user)
        return Response(
            {
                "role": role,
                "permissions": {
                    "can_manage_users": role in {UserRole.ADMIN, UserRole.MANAGER},
                    "can_update_roles": role == UserRole.ADMIN,
                    "can_record_payments": role in {UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT},
                },
            }
        )
