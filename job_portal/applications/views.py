import os

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import employer_required, seeker_required
from jobs.models import Job

from .forms import ApplicationForm
from .models import Application
from .services import REASONS, can_apply


@seeker_required
def apply(request, slug):
    job = get_object_or_404(Job.objects.select_related("company"), slug=slug)
    if job.status == Job.Status.DRAFT:
        raise Http404
    ok, reason = can_apply(request.user, job)
    if not ok:
        messages.warning(request, REASONS[reason])
        return redirect(job)
    profile = request.user.seeker_profile
    initial = {"full_name": request.user.get_full_name(), "email": request.user.email,
               "phone": profile.phone, "use_profile_cv": bool(profile.cv)}
    form = ApplicationForm(request.POST or None, request.FILES or None, initial=initial,
                           profile_cv=profile.cv if profile.cv else None)
    if request.method == "POST":
        if form.is_valid():
            app = form.save(commit=False)
            app.job, app.applicant = job, request.user
            if form.cleaned_data.get("use_profile_cv") and profile.cv and not form.cleaned_data.get("cv"):
                app.cv.name = profile.cv.name
            try:
                app.save()
            except IntegrityError:    # double-click / race: unique constraint protects us
                messages.warning(request, REASONS["already_applied"])
                return redirect(job)
            messages.success(request, f"Your application for “{job.title}” was submitted.")
            return redirect(app)
        messages.error(request, "Please correct the errors below.")
    return render(request, "applications/apply.html", {"form": form, "job": job})


@seeker_required
def my_applications(request):
    qs = Application.objects.filter(applicant=request.user).select_related("job__company")
    status = request.GET.get("status", "")
    if status in Application.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "applications/my_applications.html", {
        "page_obj": page, "status": status, "statuses": Application.Status.choices})


def _visible_applications(user):
    """Object-level access: an application is visible to its applicant, the employer who owns
    the job, and staff. Everyone else gets a 404."""
    qs = Application.objects.select_related("job__company__employer__user", "applicant")
    if user.is_staff:
        return qs
    return qs.filter(Q(applicant=user) | Q(job__company__employer__user=user))


def _get_visible(request, pk):
    if not request.user.is_authenticated:
        return None
    return get_object_or_404(_visible_applications(request.user), pk=pk)


def application_detail(request, pk):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    app = _get_visible(request, pk)
    is_employer_view = app.applicant_id != request.user.id
    return render(request, "applications/application_detail.html", {
        "app": app, "is_employer_view": is_employer_view,
        "statuses": Application.Status.choices,
        "profile": getattr(app.applicant, "seeker_profile", None) if is_employer_view else None})


def download_cv(request, pk):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    app = _get_visible(request, pk)
    if not app.cv or not os.path.exists(app.cv.path):
        raise Http404("CV file not found")
    return FileResponse(app.cv.open("rb"), as_attachment=True, filename=app.cv_filename)


@employer_required
def employer_applications(request):
    qs = Application.objects.filter(job__company__employer__user=request.user).select_related("job", "applicant")
    status, job_slug = request.GET.get("status", ""), request.GET.get("job", "")
    if status in Application.Status.values:
        qs = qs.filter(status=status)
    if job_slug:
        qs = qs.filter(job__slug=job_slug)
    my_jobs = Job.objects.filter(company__employer__user=request.user).order_by("title")
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "applications/employer_applications.html", {
        "page_obj": page, "status": status, "job_slug": job_slug,
        "statuses": Application.Status.choices, "my_jobs": my_jobs})


@employer_required
@require_POST
def update_status(request, pk):
    app = get_object_or_404(Application, pk=pk, job__company__employer__user=request.user)
    new = request.POST.get("status")
    if new not in Application.Status.values:
        messages.error(request, "Invalid status.")
    else:
        app.status = new
        app.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Application status set to {app.get_status_display()}.")
    return redirect(app)
