import os

from django.conf import settings
from django.db import models
from django.urls import reverse

from accounts.validators import validate_cv


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWED = "reviewed", "Reviewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        ACCEPTED = "accepted", "Accepted"

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    cv = models.FileField(upload_to="cvs/applications/", blank=True, validators=[validate_cv])
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "applicant"], name="unique_application_per_job")]

    def __str__(self):
        return f"{self.full_name} → {self.job.title}"

    @property
    def reference(self):
        return 1000 + self.pk

    @property
    def cv_filename(self):
        return os.path.basename(self.cv.name) if self.cv else ""

    def get_absolute_url(self):
        return reverse("applications:detail", args=[self.pk])
