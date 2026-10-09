from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import employer_required, seeker_required
from accounts.models import get_company, is_seeker
from applications.services import can_apply
from companies.models import Company

from . import constants
from .forms import JobForm
from .models import Category, Job, SavedJob
from .search import apply_filters, apply_sort

PAGE_SIZE = 10


def _saved_ids(user):
    if is_seeker(user):
        return set(SavedJob.objects.filter(user=user).values_list("job_id", flat=True))
    return set()


def _open_category_count():
    return Count("jobs", filter=Q(jobs__status="active", jobs__deadline__gte=timezone.localdate()))


def home(request):
    open_jobs = Job.objects.open().select_related("company", "category")
    categories = Category.objects.annotate(open_count=_open_category_count()).order_by("-open_count", "name")[:12]
    return render(request, "jobs/home.html", {
        "featured_jobs": open_jobs.filter(is_featured=True)[:6],
        "latest_jobs": open_jobs[:8],
        "categories": categories,
        "stats": {"jobs": Job.objects.open().count(), "companies": Company.objects.count(),
                  "categories": Category.objects.count()},
        "saved_ids": _saved_ids(request.user),
        "locations": constants.LOCATIONS,
    })


def job_list(request):
    qs = Job.objects.open().select_related("company", "category")
    qs = apply_sort(apply_filters(qs, request.GET), request.GET.get("sort"))
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    g = request.GET
    return render(request, "jobs/job_list.html", {
        "page_obj": page, "saved_ids": _saved_ids(request.user),
        "categories": Category.objects.all(), "locations": constants.LOCATIONS,
        "job_types": Job.JobType.choices, "experience_levels": Job.Experience.choices,
        "min_salaries": constants.MIN_SALARY_CHOICES, "max_salaries": constants.MAX_SALARY_CHOICES,
        "sorts": constants.SORT_CHOICES, "remote_choices": constants.REMOTE_CHOICES,
        "f": {k: g.get(k, "") for k in ("q", "category", "location", "type", "experience",
                                         "min_salary", "max_salary", "remote", "sort")},
        "has_filters": any(g.get(k) for k in ("q", "category", "location", "type", "experience",
                                              "min_salary", "max_salary", "remote")),
    })


def job_detail(request, slug):
    job = get_object_or_404(Job.objects.select_related("company", "category"), slug=slug)
    user = request.user
    company = get_company(user)
    is_owner = bool(company and company.pk == job.company_id)
    if job.status == Job.Status.DRAFT and not (is_owner or user.is_staff):
        raise Http404("Job not found")
    ok, reason = can_apply(user, job)
    return render(request, "jobs/job_detail.html", {
        "job": job, "can_apply": ok, "apply_reason": reason, "is_owner": is_owner,
        "already_applied": reason == "already_applied",
        "is_saved": job.pk in _saved_ids(user),
        "similar": Job.objects.open().filter(category=job.category).exclude(pk=job.pk)
                   .select_related("company")[:3],
    })


@seeker_required
@require_POST
def toggle_save(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if job.status == Job.Status.DRAFT:
        raise Http404
    saved, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    if created:
        messages.success(request, f"Saved “{job.title}”.")
    else:
        saved.delete()
        messages.info(request, f"Removed “{job.title}” from your saved jobs.")
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(job)


@seeker_required
def saved_jobs(request):
    qs = SavedJob.objects.filter(user=request.user).select_related("job__company", "job__category")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "jobs/saved_jobs.html", {"page_obj": page})


def category_list(request):
    cats = Category.objects.annotate(open_count=_open_category_count()).order_by("name")
    return render(request, "jobs/category_list.html", {"categories": cats})


# ---------------- employer job management ----------------
def _own_job_or_404(request, slug):
    """Object-level ownership check: only jobs of the logged-in employer's company."""
    return get_object_or_404(Job.objects.select_related("company"), slug=slug,
                             company__employer__user=request.user)


@employer_required
def employer_jobs(request):
    jobs = (Job.objects.filter(company__employer__user=request.user).select_related("category")
            .annotate(app_count=Count("applications")).order_by("-created_at", "-id"))
    status = request.GET.get("status", "")
    if status in Job.Status.values:
        jobs = jobs.filter(status=status)
    page = Paginator(jobs, 12).get_page(request.GET.get("page"))
    return render(request, "jobs/employer_jobs.html", {"page_obj": page, "status": status,
                                                       "statuses": Job.Status.choices})


@employer_required
def job_create(request):
    company = get_company(request.user)
    if company is None:
        messages.warning(request, "Please create your company profile before posting jobs.")
        return redirect("companies:manage")
    form = JobForm(request.POST or None, initial={"location": company.location})
    if request.method == "POST":
        if form.is_valid():
            job = form.save(commit=False)
            job.company = company
            job.save()
            messages.success(request, "Job posted successfully.")
            return redirect("jobs:employer_jobs")
        messages.error(request, "Please correct the errors below.")
    return render(request, "jobs/job_form.html", {"form": form, "editing": False})


@employer_required
def job_edit(request, slug):
    job = _own_job_or_404(request, slug)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated.")
            return redirect("jobs:employer_jobs")
        messages.error(request, "Please correct the errors below.")
    return render(request, "jobs/job_form.html", {"form": form, "editing": True, "job": job})


@employer_required
def job_delete(request, slug):
    job = _own_job_or_404(request, slug)
    if request.method == "POST":
        title = job.title
        job.delete()
        messages.success(request, f"“{title}” was deleted.")
        return redirect("jobs:employer_jobs")
    return render(request, "jobs/job_confirm_delete.html", {"job": job,
                                                            "app_count": job.applications.count()})


@employer_required
@require_POST
def job_close(request, slug):
    job = _own_job_or_404(request, slug)
    job.status = Job.Status.CLOSED
    job.save(update_fields=["status", "updated_at"])
    messages.info(request, f"“{job.title}” is now closed.")
    return redirect("jobs:employer_jobs")


@employer_required
@require_POST
def job_reopen(request, slug):
    job = _own_job_or_404(request, slug)
    if job.deadline_passed:
        messages.warning(request, "The deadline has passed. Edit the job and set a new deadline to reopen it.")
        return redirect("jobs:edit", slug=job.slug)
    job.status = Job.Status.ACTIVE
    job.save(update_fields=["status", "updated_at"])
    messages.success(request, f"“{job.title}” is active again.")
    return redirect("jobs:employer_jobs")
