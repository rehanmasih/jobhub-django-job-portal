from django.utils.text import slugify


def unique_slugify(instance, value, max_length=200):
    """Return a slug for `value` that is unique for instance's model."""
    model = instance.__class__
    base = slugify(value)[:max_length] or "item"
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        suffix = f"-{n}"
        slug = f"{base[:max_length - len(suffix)]}{suffix}"
        n += 1
    return slug
