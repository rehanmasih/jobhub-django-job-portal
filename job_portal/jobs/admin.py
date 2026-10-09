from django.contrib import admin
from django.db.models import Count

from .models import Category, Job, SavedJob


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "job_total")
    search_fields = ("name",)
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_jobs=Count("jobs"))

    @admin.display(description="Jobs", ordering="_jobs")
    def job_total(self, obj):
        return obj._jobs


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "location", "job_type", "experience_level",
                    "status", "is_remote", "is_featured", "deadline", "created_at")
    search_fields = ("title", "company__name", "skills_required", "description")
    list_filter = ("status", "category", "job_type", "experience_level", "is_remote", "is_featured",
                   "location", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("company", "category")
    date_hierarchy = "created_at"
    list_editable = ("is_featured",)
    actions = ["mark_closed", "mark_active"]

    @admin.action(description="Mark selected jobs as Closed")
    def mark_closed(self, request, qs):
        qs.update(status=Job.Status.CLOSED)

    @admin.action(description="Mark selected jobs as Active")
    def mark_active(self, request, qs):
        qs.update(status=Job.Status.ACTIVE)


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "created_at")
    search_fields = ("user__username", "job__title", "job__company__name")
    list_filter = ("created_at", "job__category")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    list_select_related = ("user", "job__company")
