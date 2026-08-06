from django.urls import path

from apps.accounts.views import ActiveWorkspaceView, LoginView, LogoutView, RefreshView, SessionView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("session/", SessionView.as_view(), name="auth-session"),
    path("active-workspace/", ActiveWorkspaceView.as_view(), name="auth-active-workspace"),
]
