from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from accounts.validators import validate_image_size
from job_portal.utils import unique_slugify


class CompanyQuerySet(models.QuerySet):
    def with_active_job_count(self):
        """Annotate `active_jobs`: jobs that are Active and whose deadline has not passed."""
        return self.annotate(active_jobs=Count(
            "jobs", filter=Q(jobs__status="active", jobs__deadline__gte=timezone.localdate())))


class Company(models.Model):
    """A hiring company. Belongs to (is managed by) one EmployerProfile."""
    employer = models.OneToOneField("accounts.EmployerProfile", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="company")
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, validators=[validate_image_size])
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=120, blank=True, db_index=True)
    industry = models.CharField(max_length=120, blank=True, db_index=True)
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    linkedin_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name, 220)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("companies:detail", args=[self.slug])

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p[:1].isalnum()]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    def open_jobs(self):
        return self.jobs.open()
