"""Search, filter and sort logic for the job list (kept separate so it is easy to explain)."""
from django.db.models import F, Q

from .models import Job

SORTS = {
    "newest": ("-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "salary_asc": (F("salary_min").asc(nulls_last=True), "-id"),
    "salary_desc": (F("salary_max").desc(nulls_last=True), "-id"),
    "deadline": ("deadline", "-id"),
    "title": ("title", "-id"),
}


def _int(value):
    try:
        n = int(value)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def apply_filters(qs, params):
    # 1) keyword search: every word must match title, description, skills, company or category
    for term in params.get("q", "").split()[:6]:
        qs = qs.filter(
            Q(title__icontains=term) | Q(description__icontains=term) | Q(skills_required__icontains=term)
            | Q(company__name__icontains=term) | Q(category__name__icontains=term))
    # 2) exact / partial filters
    if params.get("category"):
        qs = qs.filter(category__slug=params["category"])
    loc = params.get("location", "").strip()
    if loc:
        qs = qs.filter(Q(is_remote=True) | Q(location__icontains="remote")) if loc.lower() == "remote" \
            else qs.filter(location__icontains=loc)
    if params.get("type") in Job.JobType.values:
        qs = qs.filter(job_type=params["type"])
    if params.get("experience") in Job.Experience.values:
        qs = qs.filter(experience_level=params["experience"])
    # 3) salary: "min_salary" keeps jobs that can pay at least that much; "max_salary" jobs that start below it
    lo, hi = _int(params.get("min_salary")), _int(params.get("max_salary"))
    if lo is not None:
        qs = qs.filter(salary_max__gte=lo)
    if hi is not None:
        qs = qs.filter(salary_min__lte=hi)
    remote = params.get("remote")
    if remote == "only":
        qs = qs.filter(is_remote=True)
    elif remote == "onsite":
        qs = qs.filter(is_remote=False)
    return qs


def apply_sort(qs, key):
    return qs.order_by(*SORTS.get(key, SORTS["newest"]))
