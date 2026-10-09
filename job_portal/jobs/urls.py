from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.home, name="home"),
    path("jobs/", views.job_list, name="list"),
    path("jobs/saved/", views.saved_jobs, name="saved"),
    path("categories/", views.category_list, name="categories"),
    path("jobs/<slug:slug>/", views.job_detail, name="detail"),
    path("jobs/<slug:slug>/save/", views.toggle_save, name="toggle_save"),
    path("employer/jobs/", views.employer_jobs, name="employer_jobs"),
    path("employer/jobs/new/", views.job_create, name="create"),
    path("employer/jobs/<slug:slug>/edit/", views.job_edit, name="edit"),
    path("employer/jobs/<slug:slug>/delete/", views.job_delete, name="delete"),
    path("employer/jobs/<slug:slug>/close/", views.job_close, name="close"),
    path("employer/jobs/<slug:slug>/reopen/", views.job_reopen, name="reopen"),
]
