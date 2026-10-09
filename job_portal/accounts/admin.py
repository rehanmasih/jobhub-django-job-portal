from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import EmployerProfile, JobSeekerProfile


class SeekerInline(admin.StackedInline):
    model = JobSeekerProfile
    extra = 0
    can_delete = False


class EmployerInline(admin.StackedInline):
    model = EmployerProfile
    extra = 0
    can_delete = False


class RoleFilter(admin.SimpleListFilter):
    title = "role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return [("seeker", "Job Seeker"), ("employer", "Employer"), ("admin", "Administrator")]

    def queryset(self, request, queryset):
        v = self.value()
        if v == "seeker":
            return queryset.filter(seeker_profile__isnull=False)
        if v == "employer":
            return queryset.filter(employer_profile__isnull=False)
        if v == "admin":
            return queryset.filter(is_staff=True)
        return queryset


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [SeekerInline, EmployerInline]
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", RoleFilter)
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("seeker_profile", "employer_profile")

    @admin.display(description="Role")
    def role(self, obj):
        if obj.is_superuser:
            return "Admin"
        if hasattr(obj, "employer_profile"):
            return "Employer"
        if hasattr(obj, "seeker_profile"):
            return "Job Seeker"
        return "—"


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "professional_title", "location", "years_of_experience", "has_cv", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "professional_title", "skills", "location")
    list_filter = ("location", "years_of_experience")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_select_related = ("user",)

    @admin.display(boolean=True, description="CV")
    def has_cv(self, obj):
        return bool(obj.cv)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "phone", "created_at")
    search_fields = ("user__username", "user__email", "position")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_select_related = ("user",)
