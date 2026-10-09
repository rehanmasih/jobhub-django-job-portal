# JOBHUB — Django Job Portal

> **Find Your Dream Job. Build Your Future.**

A complete, beginner-friendly Django job portal with three roles (job seeker, employer, administrator),
search/filter/sort/pagination, applications with status tracking, saved jobs, dashboards, secure CV
uploads, a customised admin, a test suite (90 tests) and a one-command **fictional demo data generator**.

## Features
- **Job seekers:** register, edit profile, upload CV (PDF/DOC/DOCX), search and filter jobs, save/unsave, apply (upload a CV or reuse the profile CV), track applications by status, dashboard.
- **Employers:** register (a company is created automatically), edit company profile + logo, post/edit/delete/close/reopen jobs, review applications, update status, dashboard.
- **Administrators:** Django Admin for users, profiles, companies, categories, jobs, applications, saved jobs, plus a **platform statistics dashboard** at `/dashboard/platform/`.
- **Search:** title, description, skills, company, category (every word must match). **Filters:** category, location, job type, experience, min/max salary, remote/on-site. **Sorts:** newest, oldest, salary asc/desc, deadline, title. All combine, 10 jobs per page.
- **Expired jobs:** an Active job whose deadline has passed is treated as *Expired* everywhere (hidden from listings, applications blocked).
- **No fake numbers:** every statistic comes from database aggregation.

## Technology stack
Python 3.10+, Django 5.x, SQLite, Django ORM & templates, HTML5/CSS3/JavaScript, Bootstrap 5 + Bootstrap Icons (bundled locally in `static/vendor/`, so it works offline), Pillow.

## User roles
| Role | Identified by | Can |
|---|---|---|
| Job Seeker | has a `JobSeekerProfile` | profile, CV, apply, save jobs, see own applications |
| Employer | has an `EmployerProfile` (+ `Company`) | manage own company & jobs, see applications for own jobs, change status |
| Admin | `is_staff` / superuser | everything via `/admin/` and `/dashboard/platform/` |

Registration only offers Seeker/Employer; staff status can never be set from the public form.

## Database models
```
User ─┬─ JobSeekerProfile (1:1) ──< Application >── Job   (Application.applicant is the User)
      │            └───────────< SavedJob   >──────┘
      └─ EmployerProfile (1:1) ── Company (1:1) ──< Job >── Category
```
`Application` has `UniqueConstraint(job, applicant)`; `SavedJob` has `UniqueConstraint(user, job)`;
`Job` has a `CheckConstraint(salary_min <= salary_max)`. Salaries are stored as integers (PKR) and formatted only when displayed.

## Project structure
```
job_portal/
├── manage.py, requirements.txt, .env.example, .gitignore, README.md
├── job_portal/        settings, urls, shared form mixin, slug util, test factories
├── accounts/          profiles, registration, login, CV validators, role decorators, admin
├── companies/         Company model, directory, company profile management
├── jobs/              Category, Job, SavedJob, search.py (filters/sorts), views, seed_job_portal command
├── applications/      Application model, apply flow, status updates, protected CV download
├── dashboard/         seeker / employer / platform dashboards
├── templates/         base.html, error pages, shared partials (form, pagination, badges, empty state)
├── static/            css/style.css, js/main.js, vendor/ (Bootstrap)
└── media/             company_logos/, cvs/ (demo assets), profile_pictures/
```

## Installation
**Windows**
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
**Linux / macOS**
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Optional: copy `.env.example` to `.env` (set `SECRET_KEY` for anything beyond local development).

**Database**
```
python manage.py makemigrations
python manage.py migrate
```
**Create an admin** (or use the demo admin below)
```
python manage.py createsuperuser
```
**Generate demo data** (safe to run repeatedly)
```
python manage.py seed_job_portal
```
**Run**
```
python manage.py runserver
```
Open http://127.0.0.1:8000/ — admin at http://127.0.0.1:8000/admin/

## Demo accounts (all fictional) — password for every demo account: `Demo@12345`
| Role | Username |
|---|---|
| Job Seeker | `demo_seeker` (Muhammad Ali) — plus 17 more, e.g. `ayesha.khan`, `usman.ahmed` |
| Employer | `demo_employer` (owns *TechNova Solutions*) — plus 11 more, e.g. `employer_codecraft`, `employer_ai` … |
| Admin | `demo_admin` |

The seed creates ~31 users, 12 companies (with generated logos), 15 categories, 84 jobs, ~105 applications,
~75 saved jobs, and a small fictional PDF CV per job seeker. All companies use reserved `.example` domains.
**These credentials are for local demos only — never deploy them.**
`python manage.py seed_job_portal --refresh-deadlines` pushes active jobs' deadlines forward if you seeded long ago.

## Testing
```
python manage.py test
```

## Security notes
CSRF on all forms; login/role decorators; object-level ownership checks (querysets are filtered by owner, so other
people's jobs/applications return 404); CVs are validated (extension, MIME type, magic bytes, 5 MB) and are **not**
served from `/media/` — they are streamed through permission-checked views; password hashing and validators; secrets from
environment. For production also set `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, and serve media/static with a real web server.

## Interview cheat-sheet
- **One-to-One:** `User`↔`JobSeekerProfile`/`EmployerProfile`, `EmployerProfile`↔`Company`. **ForeignKey:** `Job.company`, `Job.category`, `Application.job/applicant`. **UniqueConstraint:** no duplicate applications or saved jobs — enforced by the database, not just forms.
- **Search:** `jobs/search.py` chains `Q(...)|Q(...)` with `icontains`; filters stack on one queryset; `select_related` avoids N+1 queries.
- **Dashboards:** `aggregate(Count(..., filter=Q(...)))` computes many counters in a single query.
- **Authorization:** `@seeker_required` / `@employer_required` decide *who*; queryset filters like `company__employer__user=request.user` decide *which objects*.
- **File upload:** `FileField(upload_to=..., validators=[validate_cv])`; files live under `MEDIA_ROOT`.
