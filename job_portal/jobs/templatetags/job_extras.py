from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Current GET query string with some parameters replaced (used by pagination links)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()


@register.filter
def lines(text):
    """Split a text block into non-empty lines, stripping leading bullets."""
    return [ln.strip().lstrip("-•* ").strip() for ln in (text or "").splitlines() if ln.strip()]


@register.filter
def pkr(value):
    try:
        return f"PKR {int(value):,}"
    except (TypeError, ValueError):
        return ""
