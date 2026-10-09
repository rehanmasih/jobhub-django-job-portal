from django.conf import settings
from django.db import models

from .validators import validate_cv, validate_image_size


class JobSeekerProfile(models.Model):
    """One-to-one extension of User for people looking for work."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seeker_profile")
    phone = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, validators=[validate_image_size])
    location = models.CharField(max_length=100, blank=True)
    professional_title = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=500, blank=True, help_text="Comma-separated, e.g. Python, Django, SQL")
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    portfolio = models.URLField(blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    expected_salary = models.PositiveIntegerField(null=True, blank=True, help_text="Monthly, in PKR")
    preferred_location = models.CharField(max_length=100, blank=True)
    cv = models.FileField(upload_to="cvs/", blank=True, validators=[validate_cv])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]


class EmployerProfile(models.Model):
    """One-to-one extension of User for recruiters/employers."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_profile")
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField("Your position", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Employer: {self.user.get_full_name() or self.user.username}"


def is_seeker(user):
    return user.is_authenticated and hasattr(user, "seeker_profile")


def is_employer(user):
    return user.is_authenticated and hasattr(user, "employer_profile")


def get_company(user):
    """Company owned by this employer, or None."""
    if is_employer(user):
        return getattr(user.employer_profile, "company", None)
    return None
