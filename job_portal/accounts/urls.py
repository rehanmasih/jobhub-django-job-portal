from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.JobHubLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/cv/", views.download_my_cv, name="download_cv"),
    path("password/", views.JobHubPasswordChangeView.as_view(), name="password_change"),
]
