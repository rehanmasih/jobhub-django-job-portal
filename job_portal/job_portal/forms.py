from django import forms


class BootstrapFormMixin:
    """Adds Bootstrap 5 CSS classes to every widget of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                cls = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                cls = "form-select"
            elif isinstance(w, forms.RadioSelect):
                cls = "form-check-input"
            elif isinstance(w, forms.ClearableFileInput):
                cls = "form-control"
            else:
                cls = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + cls).strip()
