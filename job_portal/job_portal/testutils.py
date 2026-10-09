"""Helper factories shared by the test suites (not a test module itself)."""
import datetime

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

PASSWORD = "Test@12345"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def pdf_file(name="cv.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def make_seeker(username="seeker"):
    from accounts.models import JobSeekerProfile
    u = User.objects.create_user(username, f"{username}@example.com", PASSWORD,
                                 first_name="Sam", last_name="Seeker")
    JobSeekerProfile.objects.create(user=u)
    return u


def make_employer(username="employer", company_name=None):
    from accounts.models import EmployerProfile
    from companies.models import Company
    u = User.objects.create_user(username, f"{username}@example.com", PASSWORD)
    ep = EmployerProfile.objects.create(user=u)
    Company.objects.create(employer=ep, name=company_name or f"{username} Ltd",
                           location="Lahore", industry="Software")
    return u


def make_category(name="Software Development"):
    from jobs.models import Category
    return Category.objects.get_or_create(name=name)[0]


def make_job(company, **kw):
    from jobs.models import Job
    data = dict(
        title="Python Developer", company=company, category=make_category(),
        description="Build things.", requirements="Python\nDjango",
        responsibilities="Write code\nReview code", location="Lahore",
        job_type=Job.JobType.FULL_TIME, experience_level=Job.Experience.ENTRY,
        salary_min=50000, salary_max=80000, skills_required="Python, Django",
        deadline=timezone.localdate() + datetime.timedelta(days=10),
        status=Job.Status.ACTIVE,
    )
    data.update(kw)
    return Job.objects.create(**data)
