import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from job_portal.testutils import PASSWORD, make_employer, make_job, make_seeker, pdf_file

from .models import Application

TMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP)
class ApplicationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.emp = make_employer("e1", "Alpha Labs")
        self.emp2 = make_employer("e2", "Beta Works")
        self.seeker = make_seeker("s")
        self.seeker2 = make_seeker("s2")
        self.job = make_job(self.emp.employer_profile.company)
        self.url = reverse("applications:apply", args=[self.job.slug])

    def data(self, **kw):
        d = {"full_name": "Sam Seeker", "email": "s@example.com", "phone": "0300", "cover_letter": "Hi", "cv": pdf_file()}
        d.update(kw)
        return d

    def login(self, u="s"):
        self.client.login(username=u, password=PASSWORD)

    def make_app(self, user=None, job=None, **kw):
        return Application.objects.create(job=job or self.job, applicant=user or self.seeker, full_name="Sam",
                                          email="s@e.com", phone="1", **kw)

    def test_apply_success_with_upload(self):
        self.login()
        r = self.client.post(self.url, self.data())
        app = Application.objects.get()
        self.assertRedirects(r, app.get_absolute_url())
        self.assertEqual((app.applicant, app.job, app.status), (self.seeker, self.job, "pending"))
        self.assertTrue(app.cv)

    def test_apply_using_profile_cv(self):
        self.login()
        p = self.seeker.seeker_profile
        p.cv = pdf_file("profile.pdf")
        p.save()
        d = self.data()
        del d["cv"]
        d["use_profile_cv"] = "on"
        self.client.post(self.url, d)
        self.assertEqual(Application.objects.get().cv.name, p.cv.name)

    def test_cv_required(self):
        self.login()
        d = self.data()
        del d["cv"]
        r = self.client.post(self.url, d)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)

    def test_invalid_cv_rejected(self):
        self.login()
        r = self.client.post(self.url, self.data(cv=SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)

    def test_duplicate_application_prevented(self):
        self.login()
        self.client.post(self.url, self.data())
        r = self.client.post(self.url, self.data(cv=pdf_file()))
        self.assertRedirects(r, self.job.get_absolute_url())
        self.assertEqual(Application.objects.count(), 1)
        with self.assertRaises(Exception):
            self.make_app()

    def test_deadline_passed_blocks_application(self):
        self.job.deadline = timezone.localdate() - datetime.timedelta(days=1)
        self.job.save()
        self.login()
        self.client.post(self.url, self.data())
        self.assertEqual(Application.objects.count(), 0)

    def test_closed_job_blocks_application(self):
        self.job.status = "closed"
        self.job.save()
        self.login()
        self.client.post(self.url, self.data())
        self.assertEqual(Application.objects.count(), 0)

    def test_employer_and_anonymous_cannot_apply(self):
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        self.login("e1")
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.assertEqual(Application.objects.count(), 0)

    def test_my_applications_filter_and_privacy(self):
        a = self.make_app()
        job2 = make_job(self.emp2.employer_profile.company, title="Other")
        self.make_app(user=self.seeker, job=job2, status="shortlisted")
        self.make_app(user=self.seeker2, job=job2)
        self.login()
        r = self.client.get(reverse("applications:mine"))
        self.assertEqual(len(r.context["page_obj"]), 2)
        r = self.client.get(reverse("applications:mine"), {"status": "shortlisted"})
        self.assertEqual([x.job.title for x in r.context["page_obj"]], ["Other"])
        r = self.client.get(reverse("applications:mine"), {"status": "accepted"})
        self.assertContains(r, "No applications with this status")

    def test_empty_my_applications(self):
        self.login()
        self.assertContains(self.client.get(reverse("applications:mine")), "haven't applied for any jobs yet")

    def test_applicant_sees_own_detail_and_reference(self):
        a = self.make_app(cover_letter="My letter")
        self.login()
        r = self.client.get(a.get_absolute_url())
        self.assertContains(r, f"Application #{a.reference}")
        self.assertContains(r, "My letter")

    def test_other_seeker_cannot_view_application(self):
        a = self.make_app()
        self.login("s2")
        self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("applications:cv", args=[a.pk])).status_code, 404)

    def test_unrelated_employer_cannot_view_or_change(self):
        a = self.make_app()
        self.login("e2")
        self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(reverse("applications:status", args=[a.pk]), {"status": "accepted"}).status_code, 404)
        a.refresh_from_db()
        self.assertEqual(a.status, "pending")

    def test_owner_employer_views_and_updates_status(self):
        a = self.make_app()
        self.login("e1")
        self.assertContains(self.client.get(a.get_absolute_url()), "Update status")
        self.client.post(reverse("applications:status", args=[a.pk]), {"status": "shortlisted"})
        a.refresh_from_db()
        self.assertEqual(a.status, "shortlisted")
        self.client.post(reverse("applications:status", args=[a.pk]), {"status": "bogus"})
        a.refresh_from_db()
        self.assertEqual(a.status, "shortlisted")

    def test_seeker_cannot_change_status(self):
        a = self.make_app()
        self.login()
        self.assertEqual(self.client.post(reverse("applications:status", args=[a.pk]), {"status": "accepted"}).status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.status, "pending")

    def test_employer_received_list_only_own_jobs(self):
        self.make_app()
        other = make_job(self.emp2.employer_profile.company, title="Other Job")
        self.make_app(user=self.seeker2, job=other)
        self.login("e1")
        r = self.client.get(reverse("applications:received"))
        self.assertEqual(len(r.context["page_obj"]), 1)
        r = self.client.get(reverse("applications:received"), {"status": "accepted"})
        self.assertContains(r, "No applications yet")

    def test_cv_download_permissions(self):
        a = self.make_app(cv=pdf_file("c.pdf"))
        self.login("e1")
        self.assertEqual(self.client.get(reverse("applications:cv", args=[a.pk])).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("applications:cv", args=[a.pk])).status_code, 302)
        self.login("s2")
        self.assertEqual(self.client.get(reverse("applications:cv", args=[a.pk])).status_code, 404)

    def test_seeker_dashboard_numbers(self):
        self.make_app(status="pending")
        job2 = make_job(self.emp.employer_profile.company, title="J2")
        self.make_app(job=job2, status="accepted")
        self.login()
        r = self.client.get(reverse("dashboard:seeker"))
        st = r.context["stats"]
        self.assertEqual((st["total"], st["pending"], st["accepted"], st["saved"]), (2, 1, 1, 0))

    def test_platform_dashboard_for_staff(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser("root", "r@e.com", PASSWORD)
        self.make_app()
        self.login("root")
        r = self.client.get(reverse("dashboard:platform"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["apps"]["total"], 1)
        self.assertEqual(r.context["users"]["seekers"], 2)
        self.assertEqual(r.context["users"]["employers"], 2)
        self.assertEqual(r.context["companies"], 2)
