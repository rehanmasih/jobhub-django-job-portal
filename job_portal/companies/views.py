from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import employer_required
from accounts.models import get_company

from .forms import CompanyForm
from .models import Company


def company_list(request):
    qs = Company.objects.with_active_job_count()
    q = request.GET.get("q", "").strip()
    industry = request.GET.get("industry", "").strip()
    location = request.GET.get("location", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(industry__icontains=q) | Q(location__icontains=q))
    if industry:
        qs = qs.filter(industry=industry)
    if location:
        qs = qs.filter(location__icontains=location)
    page = Paginator(qs.order_by("name"), 12).get_page(request.GET.get("page"))
    industries = (Company.objects.exclude(industry="").order_by("industry")
                  .values_list("industry", flat=True).distinct())
    locations = (Company.objects.exclude(location="").order_by("location")
                 .values_list("location", flat=True).distinct())
    return render(request, "companies/company_list.html", {
        "page_obj": page, "q": q, "industry": industry, "location": location,
        "industries": industries, "locations": locations,
    })


def company_detail(request, slug):
    company = get_object_or_404(Company, slug=slug)
    jobs = company.open_jobs().select_related("category", "company")
    return render(request, "companies/company_detail.html", {
        "company": company, "jobs": jobs, "job_count": jobs.count(),
        "is_owner": request.user.is_authenticated and company.employer_id
                    and company.employer.user_id == request.user.id,
    })


@employer_required
def company_manage(request):
    """Create (first time) or edit the employer's own company."""
    company = get_company(request.user)
    form = CompanyForm(request.POST or None, request.FILES or None, instance=company)
    if request.method == "POST":
        if form.is_valid():
            obj = form.save(commit=False)
            obj.employer = request.user.employer_profile     # ownership is set server-side
            obj.save()
            messages.success(request, "Company profile saved.")
            return redirect("companies:detail", slug=obj.slug)
        messages.error(request, "Please correct the errors below.")
    return render(request, "companies/company_form.html", {"form": form, "company": company})
