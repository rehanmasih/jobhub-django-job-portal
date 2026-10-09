import datetime
from io import StringIO
import shutil
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from applications.models import Application
from companies.models import Company
from job_portal.testutils import PASSWORD, make_category, make_employer, make_job, make_seeker

from .models import Category, Job, SavedJob

TMP = tempfile.mkdtemp()
today = timezone.localdate


class JobBase(TestCase):
    def setUp(self):
        self.emp = make_employer("e1", "Alpha Labs")
        self.emp2 = make_employer("e2", "Beta Works")
        self.c1 = self.emp.employer_profile.company
        self.c2 = self.emp2.employer_profile.company
        self.seeker = make_seeker("s")


class JobModelTests(JobBase):
    def test_slug_unique_and_stable(self):
        a, b = make_job(self.c1), make_job(self.c1)
        self.assertNotEqual(a.slug, b.slug)
        old = a.slug
        a.title = "Renamed"
        a.save()
        self.assertEqual(a.slug, old)

    def test_expired_detected_from_deadline(self):
        j = make_job(self.c1, deadline=today() - datetime.timedelta(days=1))
        self.assertEqual(j.effective_status, "expired")
        self.assertFalse(Job.objects.open().filter(pk=j.pk).exists())
        self.assertTrue(Job.objects.expired().filter(pk=j.pk).exists())
        Job.objects.expire_overdue()
        j.refresh_from_db()
        self.assertEqual(j.status, "expired")

    def test_salary_constraint(self):
        with self.assertRaises(Exception):
            make_job(self.c1, salary_min=100, salary_max=50)

    def test_salary_display(self):
        self.assertEqual(make_job(self.c1).salary_display, "PKR 50,000 – 80,000")
        self.assertEqual(make_job(self.c1, salary_min=None, salary_max=None).salary_display, "Negotiable")


class JobSearchTests(JobBase):
    def setUp(self):
        super().setUp()
        self.cat_ai = make_category("AI / Machine Learning")
        make_job(self.c1, title="Django Developer", skills_required="Python, Django")
        make_job(self.c1, title="ML Engineer", category=self.cat_ai, skills_required="Python, PyTorch", location="Islamabad",
                 job_type="internship", experience_level="fresh", salary_min=30000, salary_max=45000)
        make_job(self.c2, title="Accountant", category=make_category("Accounting & Finance"), skills_required="Excel",
                 location="Karachi", is_remote=True, salary_min=90000, salary_max=130000, job_type="part-time",
                 experience_level="senior")
        make_job(self.c2, title="Closed One", status="closed")
        make_job(self.c2, title="Expired One", deadline=today() - datetime.timedelta(days=2))
        make_job(self.c2, title="Draft One", status="draft")

    def titles(self, **params):
        r = self.client.get(reverse("jobs:list"), params)
        self.assertEqual(r.status_code, 200)
        return [j.title for j in r.context["page_obj"]]

    def test_only_open_jobs_listed(self):
        t = self.titles()
        self.assertEqual(len(t), 3)
        for hidden in ("Closed One", "Expired One", "Draft One"):
            self.assertNotIn(hidden, t)

    def test_search_title_skill_company_description(self):
        self.assertCountEqual(self.titles(q="python"), ["Django Developer", "ML Engineer"])   # skills
        self.assertEqual(self.titles(q="accountant"), ["Accountant"])                          # title
        self.assertCountEqual(self.titles(q="alpha"), ["Django Developer", "ML Engineer"])     # company
        self.assertEqual(len(self.titles(q="build things")), 3)                                # description
        self.assertEqual(self.titles(q="python pytorch"), ["ML Engineer"])                     # AND of terms

    def test_empty_results(self):
        r = self.client.get(reverse("jobs:list"), {"q": "zzzzz"})
        self.assertContains(r, "No jobs found.")

    def test_filters(self):
        self.assertEqual(self.titles(category=self.cat_ai.slug), ["ML Engineer"])
        self.assertEqual(self.titles(location="Karachi"), ["Accountant"])
        self.assertEqual(self.titles(location="Remote"), ["Accountant"])
        self.assertEqual(self.titles(type="internship"), ["ML Engineer"])
        self.assertEqual(self.titles(experience="senior"), ["Accountant"])
        self.assertEqual(self.titles(remote="only"), ["Accountant"])
        self.assertEqual(len(self.titles(remote="onsite")), 2)
        self.assertEqual(self.titles(min_salary="100000"), ["Accountant"])
        self.assertEqual(self.titles(max_salary="40000"), ["ML Engineer"])

    def test_filters_combine_with_search(self):
        self.assertEqual(self.titles(q="python", location="Islamabad", type="internship", experience="fresh"), ["ML Engineer"])
        self.assertEqual(self.titles(q="python", location="Karachi"), [])

    def test_invalid_filter_values_ignored(self):
        self.assertEqual(len(self.titles(type="bogus", experience="bogus", min_salary="abc")), 3)

    def test_sorting(self):
        self.assertEqual(self.titles(sort="title"), ["Accountant", "Django Developer", "ML Engineer"])
        self.assertEqual(self.titles(sort="salary_asc")[0], "ML Engineer")
        self.assertEqual(self.titles(sort="salary_desc")[0], "Accountant")
        self.assertEqual(len(self.titles(sort="deadline")), 3)
        self.assertEqual(self.titles(sort="newest")[0], "Accountant")
        self.assertEqual(self.titles(sort="oldest")[0], "Django Developer")

    def test_pagination(self):
        for i in range(15):
            make_job(self.c1, title=f"Extra {i:02d}")
        r = self.client.get(reverse("jobs:list"))
        self.assertEqual(len(r.context["page_obj"]), 10)
        self.assertEqual(r.context["page_obj"].paginator.num_pages, 2)
        r2 = self.client.get(reverse("jobs:list"), {"page": 2, "q": "extra"})
        self.assertEqual(len(r2.context["page_obj"]), 5)
        self.assertContains(r2, "q=extra")            # filters preserved in pagination links
        self.assertEqual(self.client.get(reverse("jobs:list"), {"page": "garbage"}).status_code, 200)

    def test_home_shows_db_data(self):
        make_job(self.c1, title="Star Job", is_featured=True)
        r = self.client.get(reverse("jobs:home"))
        self.assertContains(r, "Featured Jobs")
        self.assertEqual([j.title for j in r.context["featured_jobs"]], ["Star Job"])
        self.assertEqual(r.context["stats"]["jobs"], 4)

    def test_categories_page(self):
        r = self.client.get(reverse("jobs:categories"))
        self.assertContains(r, "AI / Machine Learning")


class JobDetailTests(JobBase):
    def test_detail_and_404(self):
        j = make_job(self.c1)
        r = self.client.get(j.get_absolute_url())
        self.assertContains(r, "Python Developer")
        self.assertContains(r, "Login to Apply")
        self.assertEqual(self.client.get(reverse("jobs:detail", args=["nope"])).status_code, 404)

    def test_draft_hidden_from_public_visible_to_owner(self):
        j = make_job(self.c1, status="draft")
        self.assertEqual(self.client.get(j.get_absolute_url()).status_code, 404)
        self.client.login(username="e1", password=PASSWORD)
        self.assertEqual(self.client.get(j.get_absolute_url()).status_code, 200)

    def test_expired_shows_applications_closed(self):
        j = make_job(self.c1, deadline=today() - datetime.timedelta(days=1))
        self.client.login(username="s", password=PASSWORD)
        self.assertContains(self.client.get(j.get_absolute_url()), "Applications Closed")

    def test_already_applied_and_saved_buttons(self):
        j = make_job(self.c1)
        self.client.login(username="s", password=PASSWORD)
        self.assertContains(self.client.get(j.get_absolute_url()), "Apply Now")
        Application.objects.create(job=j, applicant=self.seeker, full_name="S", email="s@e.com", phone="1")
        SavedJob.objects.create(user=self.seeker, job=j)
        r = self.client.get(j.get_absolute_url())
        self.assertContains(r, "Already Applied")
        self.assertContains(r, "Saved")


class SavedJobTests(JobBase):
    def setUp(self):
        super().setUp()
        self.job = make_job(self.c1)
        self.client.login(username="s", password=PASSWORD)
        self.url = reverse("jobs:toggle_save", args=[self.job.slug])

    def test_save_and_unsave(self):
        self.client.post(self.url)
        self.assertEqual(SavedJob.objects.filter(user=self.seeker, job=self.job).count(), 1)
        self.assertContains(self.client.get(reverse("jobs:saved")), "Python Developer")
        self.client.post(self.url)
        self.assertEqual(SavedJob.objects.count(), 0)
        self.assertContains(self.client.get(reverse("jobs:saved")), "haven't saved any jobs")

    def test_duplicate_save_prevented_by_constraint(self):
        SavedJob.objects.create(user=self.seeker, job=self.job)
        with self.assertRaises(Exception):
            SavedJob.objects.create(user=self.seeker, job=self.job)

    def test_get_not_allowed_and_open_redirect_blocked(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        r = self.client.post(self.url, {"next": "https://evil.example/"})
        self.assertRedirects(r, self.job.get_absolute_url())

    def test_employer_cannot_save(self):
        self.client.logout()
        self.client.login(username="e1", password=PASSWORD)
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_anonymous_redirected(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)


class EmployerJobTests(JobBase):
    def valid(self, **kw):
        d = {"title": "Backend Dev", "category": make_category().pk, "description": "Desc", "responsibilities": "a",
             "requirements": "b", "skills_required": "Python", "salary_min": 50000, "salary_max": 90000,
             "location": "Lahore", "job_type": "full-time", "experience_level": "entry-level",
             "deadline": (today() + datetime.timedelta(days=20)).isoformat(), "vacancies": 2, "status": "active"}
        d.update(kw)
        return d

    def login(self, u="e1"):
        self.client.login(username=u, password=PASSWORD)

    def test_create_job_assigns_own_company(self):
        self.login()
        r = self.client.post(reverse("jobs:create"), self.valid())
        self.assertRedirects(r, reverse("jobs:employer_jobs"))
        self.assertEqual(Job.objects.get(title="Backend Dev").company, self.c1)

    def test_company_cannot_be_forged_via_post(self):
        self.login()
        self.client.post(reverse("jobs:create"), self.valid(company=self.c2.pk))
        self.assertEqual(Job.objects.get(title="Backend Dev").company, self.c1)

    def test_validation_rules(self):
        self.login()
        bad = [self.valid(salary_min=90000, salary_max=50000), self.valid(title=""), self.valid(description=""),
               self.valid(category=""), self.valid(salary_min=-5),
               self.valid(deadline=(today() - datetime.timedelta(days=1)).isoformat())]
        for data in bad:
            r = self.client.post(reverse("jobs:create"), data)
            self.assertEqual(r.status_code, 200, data)
        self.assertEqual(Job.objects.count(), 0)

    def test_edit_own_job(self):
        j = make_job(self.c1)
        self.login()
        r = self.client.post(reverse("jobs:edit", args=[j.slug]), self.valid(title="Changed"))
        self.assertEqual(r.status_code, 302)
        j.refresh_from_db()
        self.assertEqual(j.title, "Changed")

    def test_other_employer_cannot_edit_delete_close(self):
        j = make_job(self.c1)
        self.login("e2")
        self.assertEqual(self.client.get(reverse("jobs:edit", args=[j.slug])).status_code, 404)
        self.assertEqual(self.client.post(reverse("jobs:edit", args=[j.slug]), self.valid(title="Hacked")).status_code, 404)
        self.assertEqual(self.client.post(reverse("jobs:delete", args=[j.slug])).status_code, 404)
        self.assertEqual(self.client.post(reverse("jobs:close", args=[j.slug])).status_code, 404)
        j.refresh_from_db()
        self.assertEqual(j.title, "Python Developer")
        self.assertEqual(j.status, "active")

    def test_delete_close_reopen(self):
        j = make_job(self.c1)
        self.login()
        self.client.post(reverse("jobs:close", args=[j.slug]))
        j.refresh_from_db()
        self.assertEqual(j.status, "closed")
        self.client.post(reverse("jobs:reopen", args=[j.slug]))
        j.refresh_from_db()
        self.assertEqual(j.status, "active")
        self.assertContains(self.client.get(reverse("jobs:delete", args=[j.slug])), "Delete")
        self.client.post(reverse("jobs:delete", args=[j.slug]))
        self.assertFalse(Job.objects.filter(pk=j.pk).exists())

    def test_reopen_after_deadline_needs_new_deadline(self):
        j = make_job(self.c1, status="closed", deadline=today() - datetime.timedelta(days=3))
        self.login()
        self.client.post(reverse("jobs:reopen", args=[j.slug]))
        j.refresh_from_db()
        self.assertEqual(j.status, "closed")

    def test_employer_job_list_only_own(self):
        make_job(self.c1, title="Mine")
        make_job(self.c2, title="Theirs")
        self.login()
        r = self.client.get(reverse("jobs:employer_jobs"))
        self.assertContains(r, "Mine")
        self.assertNotContains(r, "Theirs")

    def test_seeker_cannot_post_job(self):
        self.client.login(username="s", password=PASSWORD)
        self.assertEqual(self.client.post(reverse("jobs:create"), self.valid()).status_code, 403)
        self.assertEqual(Job.objects.count(), 0)

    def test_employer_dashboard_numbers_from_db(self):
        j = make_job(self.c1)
        make_job(self.c1, status="closed")
        Application.objects.create(job=j, applicant=self.seeker, full_name="S", email="s@e.com", phone="1")
        self.login()
        r = self.client.get(reverse("dashboard:employer"))
        self.assertEqual(r.context["job_stats"], {"posted": 2, "active": 1, "closed": 1})
        self.assertEqual(r.context["app_stats"]["total"], 1)
        self.assertEqual(r.context["app_stats"]["pending"], 1)


@override_settings(MEDIA_ROOT=TMP)
class SeedCommandTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def counts(self):
        from django.contrib.auth.models import User
        return [M.objects.count() for M in (User, Company, Category, Job, Application, SavedJob)]

    def test_seed_creates_data_and_is_repeatable(self):
        call_command("seed_job_portal", stdout=StringIO())
        users, companies, cats, jobs, apps, saved = self.counts()
        self.assertGreaterEqual(companies, 10)
        self.assertGreaterEqual(cats, 12)
        self.assertGreaterEqual(jobs, 50)
        self.assertGreaterEqual(apps, 50)
        self.assertGreater(saved, 0)
        self.assertGreaterEqual(users, 15)
        call_command("seed_job_portal", stdout=StringIO())
        self.assertEqual(self.counts(), [users, companies, cats, jobs, apps, saved])

    def test_seed_relationships_are_valid(self):
        from django.contrib.auth.models import User
        call_command("seed_job_portal", stdout=StringIO())
        self.assertEqual(Job.objects.filter(company__isnull=True).count(), 0)
        self.assertEqual(Application.objects.exclude(applicant__seeker_profile__isnull=False).count(), 0)
        self.assertEqual(Company.objects.filter(employer__isnull=True).count(), 0)
        self.assertTrue(User.objects.get(username="demo_seeker").check_password("Demo@12345"))
        self.assertTrue(User.objects.get(username="demo_employer").employer_profile.company.jobs.exists())
        for c in Company.objects.all():
            self.assertTrue(c.logo and c.logo.storage.exists(c.logo.name))
        for app in Application.objects.all():
            self.assertTrue(app.cv.storage.exists(app.cv.name))
        self.assertFalse(Job.objects.filter(salary_min__gt=models_F()).exists())


def models_F():
    from django.db.models import F
    return F("salary_max")
