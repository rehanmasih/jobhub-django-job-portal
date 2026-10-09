from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("seeker/", views.seeker_dashboard, name="seeker"),
    path("employer/", views.employer_dashboard, name="employer"),
    path("platform/", views.platform_dashboard, name="platform"),
]
