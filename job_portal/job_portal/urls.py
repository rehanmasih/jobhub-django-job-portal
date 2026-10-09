from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "JOBHUB Administration"
admin.site.site_title = "JOBHUB Admin"
admin.site.index_title = "Manage the job portal"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("companies/", include("companies.urls")),
    path("applications/", include("applications.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("jobs.urls")),
    # Only public assets are served from /media/. CVs are NOT exposed here:
    # they are delivered through permission-checked views.
    re_path(r"^media/(?P<path>(?:company_logos|profile_pictures)/.*)$", serve,
            {"document_root": settings.MEDIA_ROOT}),
]

handler403 = "job_portal.views.permission_denied"
