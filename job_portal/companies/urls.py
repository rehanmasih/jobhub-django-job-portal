from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("", views.company_list, name="list"),
    path("manage/", views.company_manage, name="manage"),
    path("<slug:slug>/", views.company_detail, name="detail"),
]
