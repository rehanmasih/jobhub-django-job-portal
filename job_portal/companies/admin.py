from django.contrib import admin
from django.db.models import Count

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "location", "employee_count", "employer", "job_total", "created_at")
    search_fields = ("name", "industry", "location", "email")
    list_filter = ("industry", "location")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("employer__user",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_jobs=Count("jobs"))

    @admin.display(description="Jobs", ordering="_jobs")
    def job_total(self, obj):
        return obj._jobs
