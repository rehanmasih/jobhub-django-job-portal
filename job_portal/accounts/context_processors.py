from .models import get_company, is_employer, is_seeker


def roles(request):
    """Expose the user's role to every template (used by the navbar)."""
    user = request.user
    return {
        "is_seeker": is_seeker(user),
        "is_employer": is_employer(user),
        "my_company": get_company(user),
    }
