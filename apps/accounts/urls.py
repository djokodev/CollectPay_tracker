from django.urls import path

from apps.accounts.views import (
    LoginView,
    LogoutView,
    MyPermissionsView,
    ProfileView,
    RefreshView,
    RegisterView,
    UserListView,
    UserRoleUpdateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("users/", UserListView.as_view(), name="auth-users-list"),
    path("users/<int:user_id>/role/", UserRoleUpdateView.as_view(), name="auth-user-role-update"),
    path("my-permissions/", MyPermissionsView.as_view(), name="auth-my-permissions"),
]
