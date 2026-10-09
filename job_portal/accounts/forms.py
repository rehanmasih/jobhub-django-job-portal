from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from companies.models import Company
from job_portal.forms import BootstrapFormMixin

from .models import EmployerProfile, JobSeekerProfile
from .validators import validate_cv

ROLE_CHOICES = [("seeker", "Job Seeker — I'm looking for work"), ("employer", "Employer — I'm hiring")]


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Creates a User plus the matching profile. Only the two public roles can be chosen;
    staff/superuser status can never be set from here (no privilege escalation)."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial="seeker")
    company_name = forms.CharField(max_length=200, required=False, help_text="Employers only — you can complete the company profile later.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == "employer" and not data.get("company_name", "").strip():
            self.add_error("company_name", "Please enter your company name.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        if self.cleaned_data["role"] == "employer":
            profile = EmployerProfile.objects.create(user=user)
            Company.objects.create(employer=profile, name=self.cleaned_data["company_name"].strip(),
                                   email=user.email)
        else:
            JobSeekerProfile.objects.create(user=user)
        return user


class SeekerProfileForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    cv = forms.FileField(required=False, validators=[validate_cv],
                         widget=forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"}),
                         help_text="PDF, DOC or DOCX — max 5 MB.")

    class Meta:
        model = JobSeekerProfile
        fields = ["phone", "profile_picture", "location", "professional_title", "bio", "skills",
                  "education", "experience", "years_of_experience", "expected_salary",
                  "preferred_location", "linkedin", "github", "portfolio", "cv"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4}),
                   "education": forms.Textarea(attrs={"rows": 3}),
                   "experience": forms.Textarea(attrs={"rows": 3})}

    field_order = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("This email is used by another account.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile.save()
        return profile
