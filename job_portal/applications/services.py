from accounts.models import is_seeker

REASONS = {
    "anonymous": "Please log in as a job seeker to apply.",
    "not_seeker": "Only job seeker accounts can apply for jobs.",
    "not_active": "This job is not accepting applications.",
    "deadline": "Applications Closed — the deadline has passed.",
    "already_applied": "You have already applied for this job.",
}


def can_apply(user, job):
    """Return (allowed, reason_code). Mirrors the 5 business rules for applying."""
    from .models import Application
    if not user.is_authenticated:
        return False, "anonymous"
    if not is_seeker(user):
        return False, "not_seeker"
    if job.status != "active":
        return False, "not_active"
    if job.deadline_passed:
        return False, "deadline"
    if Application.objects.filter(job=job, applicant=user).exists():
        return False, "already_applied"
    return True, ""
