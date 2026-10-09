from django import forms
from django.utils import timezone

from job_portal.forms import BootstrapFormMixin

from .models import Job


class JobForm(BootstrapFormMixin, forms.ModelForm):
    status = forms.ChoiceField(choices=[(Job.Status.DRAFT, "Draft (hidden)"), (Job.Status.ACTIVE, "Active (published)"),
                                        (Job.Status.CLOSED, "Closed")], initial=Job.Status.ACTIVE)

    class Meta:
        model = Job
        fields = ["title", "category", "description", "responsibilities", "requirements", "skills_required",
                  "education_required", "salary_min", "salary_max", "location", "job_type", "experience_level",
                  "is_remote", "deadline", "vacancies", "status"]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 5}),
            "responsibilities": forms.Textarea(attrs={"rows": 4, "placeholder": "One responsibility per line"}),
            "requirements": forms.Textarea(attrs={"rows": 4, "placeholder": "One requirement per line"}),
            "skills_required": forms.TextInput(attrs={"placeholder": "Python, Django, SQL"}),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Job title is required.")
        return title

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        unchanged = self.instance.pk and deadline == self.instance.deadline
        if deadline < timezone.localdate() and not unchanged:
            raise forms.ValidationError("The deadline cannot be in the past.")
        return deadline

    def clean(self):
        data = super().clean()
        lo, hi = data.get("salary_min"), data.get("salary_max")
        if lo is not None and hi is not None and lo > hi:
            self.add_error("salary_max", "Maximum salary must be greater than or equal to the minimum.")
        return data
