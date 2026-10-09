import os

from django.conf import settings
from django.core.exceptions import ValidationError

CV_EXTENSIONS = {".pdf", ".doc", ".docx"}
CV_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some browsers send this for .doc files
}
# "Magic numbers": the first bytes of genuine files of each type.
_MAGIC = {".pdf": (b"%PDF",), ".doc": (b"\xd0\xcf\x11\xe0",), ".docx": (b"PK\x03\x04",)}


def validate_cv(file):
    """Accept only real PDF/DOC/DOCX files up to CV_MAX_UPLOAD_SIZE."""
    if getattr(file, "_committed", False):   # already stored, nothing new to check
        return
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in CV_EXTENSIONS:
        raise ValidationError("Unsupported file type. Please upload a PDF, DOC or DOCX file.")
    if file.size > settings.CV_MAX_UPLOAD_SIZE:
        raise ValidationError(f"File too large. Maximum size is {settings.CV_MAX_UPLOAD_SIZE // (1024 * 1024)} MB.")
    content_type = getattr(file, "content_type", None) or getattr(getattr(file, "file", None), "content_type", None)
    if content_type and content_type not in CV_MIME_TYPES:
        raise ValidationError("The file's content type is not allowed for a CV.")
    head = file.read(8)
    file.seek(0)
    if not any(head.startswith(m) for m in _MAGIC[ext]):
        raise ValidationError("The file content does not match its extension.")


def validate_image_size(file):
    if getattr(file, "_committed", False):
        return
    if file.size > settings.IMAGE_MAX_UPLOAD_SIZE:
        raise ValidationError(f"Image too large. Maximum size is {settings.IMAGE_MAX_UPLOAD_SIZE // (1024 * 1024)} MB.")
