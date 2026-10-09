from django import forms

from accounts.validators import validate_cv
from job_portal.forms import BootstrapFormMixin

from .models import Application


class ApplicationForm(BootstrapFormMixin, forms.ModelForm):
    use_profile_cv = forms.BooleanField(required=False, label="Use the CV from my profile")
    cv = forms.FileField(required=False, validators=[validate_cv], label="Upload a CV",
                         widget=forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"}),
                         help_text="PDF, DOC or DOCX — max 5 MB.")

    class Meta:
        model = Application
        fields = ["full_name", "email", "phone", "cv", "cover_letter"]
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, profile_cv=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_cv = profile_cv
        if not profile_cv:
            del self.fields["use_profile_cv"]
        self.fields["phone"].required = True

    def clean(self):
        data = super().clean()
        use_profile = data.get("use_profile_cv") and self.profile_cv
        if not use_profile and not data.get("cv"):
            self.add_error("cv", "Please upload a CV or use the one from your profile.")
        return data
