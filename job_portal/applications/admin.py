from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "job", "company", "status", "created_at")
    search_fields = ("full_name", "email", "job__title", "job__company__name", "applicant__username")
    list_filter = ("status", "job__company", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("job__company", "applicant")
    list_editable = ("status",)

    @admin.display(description="Company", ordering="job__company__name")
    def company(self, obj):
        return obj.job.company
