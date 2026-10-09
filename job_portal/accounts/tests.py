import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from job_portal.testutils import PASSWORD, make_employer, make_seeker, pdf_file

from .models import EmployerProfile, JobSeekerProfile, is_employer, is_seeker

TMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP)
class AuthTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def reg(self, **kw):
        data = dict(username="newuser", first_name="New", last_name="User", email="new@example.com",
                    password1="Str0ng!Pass#77", password2="Str0ng!Pass#77", role="seeker")
        data.update(kw)
        return self.client.post(reverse("accounts:register"), data)

    def test_register_seeker_creates_profile(self):
        r = self.reg()
        self.assertRedirects(r, reverse("accounts:profile"))
        u = User.objects.get(username="newuser")
        self.assertTrue(is_seeker(u) and not is_employer(u))
        self.assertFalse(u.is_staff)

    def test_register_employer_creates_profile_and_company(self):
        r = self.reg(username="boss", email="b@example.com", role="employer", company_name="Acme Fictional")
        self.assertRedirects(r, reverse("companies:manage"))
        u = User.objects.get(username="boss")
        self.assertTrue(is_employer(u))
        self.assertEqual(u.employer_profile.company.name, "Acme Fictional")

    def test_employer_requires_company_name(self):
        r = self.reg(role="employer")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_cannot_register_as_admin(self):
        r = self.reg(role="admin", is_staff="on", is_superuser="on")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.reg(is_staff="on", is_superuser="on")
        u = User.objects.get(username="newuser")
        self.assertFalse(u.is_staff or u.is_superuser)

    def test_weak_password_rejected(self):
        r = self.reg(password1="12345678", password2="12345678")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertEqual(r.status_code, 200)

    def test_duplicate_email_rejected(self):
        make_seeker("a")
        r = self.reg(email="a@example.com")
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_login_logout(self):
        make_seeker("sam")
        self.assertTrue(self.client.login(username="sam", password=PASSWORD))
        r = self.client.post(reverse("accounts:login"), {"username": "sam", "password": PASSWORD})
        self.assertEqual(r.status_code, 302)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_bad_login(self):
        make_seeker("sam")
        r = self.client.post(reverse("accounts:login"), {"username": "sam", "password": "wrong"})
        self.assertContains(r, "Please enter a correct")

    def test_password_is_hashed(self):
        make_seeker("sam")
        self.assertNotEqual(User.objects.get(username="sam").password, PASSWORD)

    def test_password_change(self):
        make_seeker("sam")
        self.client.login(username="sam", password=PASSWORD)
        r = self.client.post(reverse("accounts:password_change"), {
            "old_password": PASSWORD, "new_password1": "An0ther!Pass#88", "new_password2": "An0ther!Pass#88"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.get(username="sam").check_password("An0ther!Pass#88"))

    def test_login_required_pages(self):
        for name in ("accounts:profile", "dashboard:home", "jobs:saved", "applications:mine"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_dashboard_redirects_by_role(self):
        make_seeker("s")
        make_employer("e")
        User.objects.create_superuser("root", "r@example.com", PASSWORD)
        for user, target in (("s", "dashboard:seeker"), ("e", "dashboard:employer"), ("root", "dashboard:platform")):
            self.client.login(username=user, password=PASSWORD)
            self.assertRedirects(self.client.get(reverse("dashboard:home")), reverse(target))
            self.client.logout()

    def test_seeker_cannot_open_employer_pages(self):
        make_seeker("s")
        self.client.login(username="s", password=PASSWORD)
        for name in ("jobs:create", "jobs:employer_jobs", "companies:manage", "applications:received", "dashboard:employer"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_employer_cannot_open_seeker_pages(self):
        make_employer("e")
        self.client.login(username="e", password=PASSWORD)
        for name in ("jobs:saved", "applications:mine", "dashboard:seeker"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_non_staff_cannot_open_platform_dashboard(self):
        make_seeker("s")
        self.client.login(username="s", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("dashboard:platform")).status_code, 403)

    def test_one_to_one_profile(self):
        u = make_seeker("s")
        with self.assertRaises(Exception):
            JobSeekerProfile.objects.create(user=u)


@override_settings(MEDIA_ROOT=TMP)
class ProfileCvTests(TestCase):
    def setUp(self):
        self.user = make_seeker("s")
        self.client.login(username="s", password=PASSWORD)

    def post(self, cv=None):
        data = {"first_name": "Sam", "last_name": "Seeker", "email": "s@example.com", "years_of_experience": 1}
        if cv:
            data["cv"] = cv
        return self.client.post(reverse("accounts:profile"), data)

    def test_profile_edit(self):
        r = self.post()
        self.assertRedirects(r, reverse("accounts:profile"))

    def test_valid_cv_upload_and_download(self):
        self.post(pdf_file("mycv.pdf"))
        self.user.seeker_profile.refresh_from_db()
        self.assertTrue(self.user.seeker_profile.cv.name.startswith("cvs/"))
        r = self.client.get(reverse("accounts:download_cv"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])

    def test_invalid_extension_rejected(self):
        r = self.post(SimpleUploadedFile("evil.exe", b"MZ\x90\x00", content_type="application/octet-stream"))
        self.assertEqual(r.status_code, 200)
        self.user.seeker_profile.refresh_from_db()
        self.assertFalse(self.user.seeker_profile.cv)

    def test_fake_pdf_rejected(self):
        r = self.post(SimpleUploadedFile("evil.pdf", b"MZ\x90\x00 not a pdf", content_type="application/pdf"))
        self.assertContains(r, "does not match")

    def test_wrong_mime_rejected(self):
        r = self.post(SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="application/x-msdownload"))
        self.assertEqual(r.status_code, 200)
        self.user.seeker_profile.refresh_from_db()
        self.assertFalse(self.user.seeker_profile.cv)

    def test_oversized_cv_rejected(self):
        big = SimpleUploadedFile("big.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024 + 10), content_type="application/pdf")
        r = self.post(big)
        self.assertContains(r, "too large")

    def test_docx_signature_accepted(self):
        f = SimpleUploadedFile("cv.docx", b"PK\x03\x04rest", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.post(f)
        self.user.seeker_profile.refresh_from_db()
        self.assertTrue(self.user.seeker_profile.cv)

    def test_cv_not_served_from_media_url(self):
        self.post(pdf_file())
        name = self.user.seeker_profile.cv.name
        self.assertEqual(self.client.get("/media/" + name).status_code, 404)

    def test_download_without_cv_is_404(self):
        self.assertEqual(self.client.get(reverse("accounts:download_cv")).status_code, 404)
