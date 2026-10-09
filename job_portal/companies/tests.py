import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from job_portal.testutils import PASSWORD, make_employer, make_job, make_seeker

from .models import Company

TMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP)
class CompanyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.emp = make_employer("e1", "Alpha Labs")
        self.emp2 = make_employer("e2", "Beta Works")
        self.c1 = self.emp.employer_profile.company

    def test_slug_generated_and_unique(self):
        c = Company.objects.create(name="Alpha Labs")
        self.assertNotEqual(c.slug, self.c1.slug)
        self.assertTrue(c.slug.startswith("alpha-labs"))

    def test_company_list_and_search(self):
        r = self.client.get(reverse("companies:list"))
        self.assertContains(r, "Alpha Labs")
        r = self.client.get(reverse("companies:list"), {"q": "beta"})
        self.assertContains(r, "Beta Works")
        self.assertNotContains(r, "Alpha Labs")
        r = self.client.get(reverse("companies:list"), {"q": "zzzz"})
        self.assertContains(r, "No companies found")

    def test_company_filter_by_industry(self):
        Company.objects.filter(pk=self.c1.pk).update(industry="Finance")
        r = self.client.get(reverse("companies:list"), {"industry": "Finance"})
        self.assertContains(r, "Alpha Labs")
        self.assertNotContains(r, "Beta Works")

    def test_active_job_count(self):
        make_job(self.c1)
        make_job(self.c1, title="Old", status="closed")
        c = Company.objects.with_active_job_count().get(pk=self.c1.pk)
        self.assertEqual(c.active_jobs, 1)

    def test_detail_lists_only_active_jobs(self):
        make_job(self.c1, title="Visible Job")
        make_job(self.c1, title="Closed Job", status="closed")
        r = self.client.get(self.c1.get_absolute_url())
        self.assertContains(r, "Visible Job")
        self.assertNotContains(r, "Closed Job")

    def test_detail_empty_state_and_404(self):
        self.assertContains(self.client.get(self.c1.get_absolute_url()), "no active jobs")
        self.assertEqual(self.client.get(reverse("companies:detail", args=["nope"])).status_code, 404)

    def test_employer_edits_own_company(self):
        self.client.login(username="e1", password=PASSWORD)
        r = self.client.post(reverse("companies:manage"), {"name": "Alpha Labs", "industry": "AI", "location": "Karachi"})
        self.assertEqual(r.status_code, 302)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.industry, "AI")
        self.assertEqual(self.c1.employer, self.emp.employer_profile)

    def test_employer_cannot_touch_other_company(self):
        self.client.login(username="e1", password=PASSWORD)
        self.client.post(reverse("companies:manage"), {"name": "Alpha Labs", "industry": "AI"})
        c2 = self.emp2.employer_profile.company
        c2.refresh_from_db()
        self.assertNotEqual(c2.industry, "AI")

    def test_employer_without_company_can_create(self):
        Company.objects.all().delete()
        self.client.login(username="e1", password=PASSWORD)
        r = self.client.post(reverse("companies:manage"), {"name": "Fresh Co"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Company.objects.get(employer__user=self.emp).name, "Fresh Co")

    def test_seeker_cannot_manage_company(self):
        make_seeker("s")
        self.client.login(username="s", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("companies:manage")).status_code, 403)

    def test_logo_placeholder_never_broken(self):
        self.assertContains(self.client.get(reverse("companies:list")), "logo-initials")
