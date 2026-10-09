from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import is_employer, is_seeker


def _role_required(check, message):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not check(request.user):
                messages.error(request, message)
                raise PermissionDenied(message)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


seeker_required = _role_required(is_seeker, "This page is only available to job seekers.")
employer_required = _role_required(is_employer, "This page is only available to employers.")
staff_required = _role_required(lambda u: u.is_staff, "This page is only available to administrators.")
