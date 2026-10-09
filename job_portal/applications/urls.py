from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("my/", views.my_applications, name="mine"),
    path("received/", views.employer_applications, name="received"),
    path("apply/<slug:slug>/", views.apply, name="apply"),
    path("<int:pk>/", views.application_detail, name="detail"),
    path("<int:pk>/cv/", views.download_cv, name="cv"),
    path("<int:pk>/status/", views.update_status, name="status"),
]
