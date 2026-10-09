from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from job_portal.utils import unique_slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Bootstrap Icons class, e.g. bi-code-slash")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name, 120)
        super().save(*args, **kwargs)


class JobQuerySet(models.QuerySet):
    def open(self):
        """Jobs people can apply to right now: Active AND deadline not passed."""
        return self.filter(status=Job.Status.ACTIVE, deadline__gte=timezone.localdate())

    def expired(self):
        today = timezone.localdate()
        return self.filter(Q(status=Job.Status.EXPIRED) | Q(status=Job.Status.ACTIVE, deadline__lt=today))

    def expire_overdue(self):
        """Persist the 'expired' status for active jobs whose deadline has passed."""
        return self.filter(status=Job.Status.ACTIVE, deadline__lt=timezone.localdate()).update(status=Job.Status.EXPIRED)


class Job(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = "full-time", "Full Time"
        PART_TIME = "part-time", "Part Time"
        INTERNSHIP = "internship", "Internship"
        CONTRACT = "contract", "Contract"
        REMOTE = "remote", "Remote"
        FREELANCE = "freelance", "Freelance"

    class Experience(models.TextChoices):
        FRESH = "fresh", "Fresh"
        ENTRY = "entry-level", "Entry Level"
        INTERMEDIATE = "intermediate", "Intermediate"
        SENIOR = "senior", "Senior"
        EXPERT = "expert", "Expert"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        EXPIRED = "expired", "Expired"

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="jobs")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="jobs")
    description = models.TextField()
    requirements = models.TextField(blank=True, help_text="One requirement per line")
    responsibilities = models.TextField(blank=True, help_text="One responsibility per line")
    salary_min = models.PositiveIntegerField(null=True, blank=True, help_text="Monthly, PKR")
    salary_max = models.PositiveIntegerField(null=True, blank=True, help_text="Monthly, PKR")
    location = models.CharField(max_length=100, db_index=True)
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME, db_index=True)
    experience_level = models.CharField(max_length=20, choices=Experience.choices, default=Experience.ENTRY, db_index=True)
    is_remote = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    deadline = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    skills_required = models.CharField(max_length=500, blank=True, help_text="Comma-separated")
    education_required = models.CharField(max_length=150, blank=True)
    vacancies = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "deadline"], name="job_status_deadline_idx")]
        constraints = [
            models.CheckConstraint(
                check=Q(salary_min__isnull=True) | Q(salary_max__isnull=True) | Q(salary_min__lte=models.F("salary_max")),
                name="job_salary_min_lte_max"),
        ]

    def __str__(self):
        return f"{self.title} — {self.company.name}"

    def clean(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValidationError({"salary_max": "Maximum salary must be greater than or equal to the minimum."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, f"{self.title}-{self.company.name}", 255)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("jobs:detail", args=[self.slug])

    # --- status helpers -------------------------------------------------
    @property
    def deadline_passed(self):
        return self.deadline < timezone.localdate()

    @property
    def effective_status(self):
        """Status as users should see it: an Active job past its deadline is Expired."""
        if self.status == self.Status.ACTIVE and self.deadline_passed:
            return self.Status.EXPIRED.value
        return self.status

    @property
    def effective_status_label(self):
        return self.Status(self.effective_status).label

    @property
    def is_open(self):
        return self.effective_status == self.Status.ACTIVE

    @property
    def days_left(self):
        return (self.deadline - timezone.localdate()).days

    # --- display helpers -------------------------------------------------
    @property
    def salary_display(self):
        lo, hi = self.salary_min, self.salary_max
        if lo is None and hi is None:
            return "Negotiable"
        if lo is not None and hi is not None:
            return f"PKR {lo:,} – {hi:,}"
        return f"PKR {lo:,}+" if lo is not None else f"Up to PKR {hi:,}"

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills_required.split(",") if s.strip()]


class SavedJob(models.Model):
    """Many-to-many between User and Job, stored explicitly so we can add created_at."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_jobs")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "job"], name="unique_saved_job")]

    def __str__(self):
        return f"{self.user} saved {self.job.title}"
