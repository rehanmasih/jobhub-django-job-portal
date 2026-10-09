from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import employer_required, seeker_required, staff_required
from accounts.models import is_employer, is_seeker
from applications.models import Application
from companies.models import Company
from jobs.models import Category, Job, SavedJob


@login_required
def home(request):
    """Send each user to the dashboard for their role."""
    u = request.user
    if u.is_staff:
        return redirect("dashboard:platform")
    if is_employer(u):
        return redirect("dashboard:employer")
    if is_seeker(u):
        return redirect("dashboard:seeker")
    messages.warning(request, "Your account has no profile yet. Please complete your profile.")
    return redirect("accounts:profile")


@seeker_required
def seeker_dashboard(request):
    apps = Application.objects.filter(applicant=request.user)
    S = Application.Status
    stats = apps.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=S.PENDING)),
        reviewed=Count("id", filter=Q(status=S.REVIEWED)),
        shortlisted=Count("id", filter=Q(status=S.SHORTLISTED)),
        rejected=Count("id", filter=Q(status=S.REJECTED)),
        accepted=Count("id", filter=Q(status=S.ACCEPTED)),
    )
    stats["saved"] = SavedJob.objects.filter(user=request.user).count()
    return render(request, "dashboard/seeker.html", {
        "stats": stats, "recent": apps.select_related("job__company")[:5],
        "profile": request.user.seeker_profile})


@employer_required
def employer_dashboard(request):
    today = timezone.localdate()
    jobs = Job.objects.filter(company__employer__user=request.user)
    job_stats = jobs.aggregate(
        posted=Count("id"),
        active=Count("id", filter=Q(status=Job.Status.ACTIVE, deadline__gte=today)),
        closed=Count("id", filter=Q(status=Job.Status.CLOSED)),
    )
    apps = Application.objects.filter(job__company__employer__user=request.user)
    app_stats = apps.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Application.Status.PENDING)),
        shortlisted=Count("id", filter=Q(status=Application.Status.SHORTLISTED)),
    )
    return render(request, "dashboard/employer.html", {
        "job_stats": job_stats, "app_stats": app_stats,
        "recent_apps": apps.select_related("job", "applicant")[:6],
        "recent_jobs": jobs.select_related("category").annotate(app_count=Count("applications")).order_by("-created_at", "-id")[:5],
    })


@staff_required
def platform_dashboard(request):
    today = timezone.localdate()
    users = User.objects.aggregate(
        total=Count("id"),
        seekers=Count("id", filter=Q(seeker_profile__isnull=False)),
        employers=Count("id", filter=Q(employer_profile__isnull=False)))
    jobs = Job.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Job.Status.ACTIVE, deadline__gte=today)),
        closed=Count("id", filter=Q(status=Job.Status.CLOSED)))
    apps = Application.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Application.Status.PENDING)),
        shortlisted=Count("id", filter=Q(status=Application.Status.SHORTLISTED)))
    return render(request, "dashboard/platform.html", {
        "users": users, "jobs": jobs, "apps": apps,
        "companies": Company.objects.count(),
        "saved": SavedJob.objects.count(),
        "latest_jobs": Job.objects.select_related("company")[:6],
        "latest_apps": Application.objects.select_related("job__company", "applicant")[:6],
        "top_categories": Category.objects.annotate(n=Count("jobs")).order_by("-n", "name")[:6],
        "top_companies": Company.objects.annotate(n=Count("jobs")).order_by("-n", "name")[:6],
    })
