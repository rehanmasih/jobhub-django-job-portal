from django import forms

from job_portal.forms import BootstrapFormMixin

from .models import Company


class CompanyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "logo", "description", "industry", "location", "employee_count", "founded_year",
                  "website", "email", "phone", "linkedin_url", "facebook_url", "twitter_url"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_founded_year(self):
        year = self.cleaned_data.get("founded_year")
        if year and not (1800 <= year <= 2100):
            raise forms.ValidationError("Enter a valid year.")
        return year
