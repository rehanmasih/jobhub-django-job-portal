import os

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .decorators import seeker_required
from .forms import LoginForm, RegistrationForm, SeekerProfileForm, StyledPasswordChangeForm
from .models import JobSeekerProfile, is_employer


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegistrationForm(request.POST or None, initial={"role": request.GET.get("role", "seeker")})
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if form.cleaned_data["role"] == "employer":
            messages.success(request, "Welcome to JOBHUB! Please complete your company profile.")
            return redirect("companies:manage")
        messages.success(request, "Welcome to JOBHUB! Complete your profile and upload your CV to start applying.")
        return redirect("accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


class JobHubLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
        return super().form_valid(form)


class JobHubPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("dashboard:home")
    success_message = "Your password was changed successfully."


@login_required
def profile(request):
    """Edit the job seeker profile (employers are sent to their company page)."""
    if is_employer(request.user):
        messages.info(request, "Employers manage their details on the company profile page.")
        return redirect("companies:manage")
    if request.user.is_staff and not hasattr(request.user, "seeker_profile"):
        messages.info(request, "Administrator accounts do not have a job seeker profile.")
        return redirect("dashboard:home")
    obj, created = JobSeekerProfile.objects.get_or_create(user=request.user)   # handles a missing profile
    if created:
        messages.info(request, "We created an empty profile for you — please fill it in.")
    form = SeekerProfileForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
    return render(request, "accounts/profile.html", {"form": form, "profile": obj})


@seeker_required
def download_my_cv(request):
    cv = request.user.seeker_profile.cv
    if not cv or not os.path.exists(cv.path):
        messages.warning(request, "You haven't uploaded a CV yet.")
        raise Http404("No CV")
    return FileResponse(cv.open("rb"), as_attachment=True, filename=os.path.basename(cv.name))
