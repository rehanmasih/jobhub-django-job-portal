"""Generate realistic FICTIONAL demo data:  python manage.py seed_job_portal

Safe to run repeatedly: every record is looked up with get_or_create and the random
generator is seeded, so a second run creates nothing new.
"""
import datetime
import os
import random
import textwrap

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import EmployerProfile, JobSeekerProfile
from applications.models import Application
from companies.models import Company
from jobs.models import Category, Job, SavedJob

DEMO_PASSWORD = "Demo@12345"

CATEGORIES = [
    ("Software Development", "bi-code-slash"), ("Web Development", "bi-globe2"),
    ("AI / Machine Learning", "bi-cpu"), ("Data Science", "bi-bar-chart-line"),
    ("Mobile Development", "bi-phone"), ("UI/UX Design", "bi-palette"),
    ("Cyber Security", "bi-shield-lock"), ("DevOps", "bi-diagram-3"),
    ("Cloud Computing", "bi-cloud"), ("Digital Marketing", "bi-megaphone"),
    ("Accounting & Finance", "bi-cash-coin"), ("Human Resources", "bi-people"),
    ("Sales", "bi-graph-up-arrow"), ("Customer Support", "bi-headset"),
    ("Project Management", "bi-kanban"),
]

# category -> (summary, responsibilities, requirements, education)
CAT_TEXT = {
    "Software Development": ("design, build and maintain reliable software", ["Design and implement clean, testable code", "Take part in code reviews and sprint planning", "Fix bugs and improve performance", "Write technical documentation"], ["Solid programming fundamentals", "Experience with Git and version control", "Good problem-solving skills", "Ability to work in a team"], "BS Computer Science or equivalent"),
    "Web Development": ("build fast, accessible web applications", ["Develop features for web applications", "Build and consume REST APIs", "Optimise pages for speed and usability", "Collaborate with designers and QA"], ["Knowledge of HTML, CSS and JavaScript", "Understanding of HTTP and REST", "Experience with relational databases", "Familiarity with Git"], "BS Computer Science / Software Engineering"),
    "AI / Machine Learning": ("develop and deploy machine learning solutions", ["Train, evaluate and tune ML models", "Prepare and clean datasets", "Deploy models behind APIs", "Document experiments and results"], ["Strong Python skills", "Knowledge of ML algorithms and statistics", "Experience with scikit-learn, PyTorch or TensorFlow", "Ability to explain results clearly"], "BS/MS in Computer Science, AI or Data Science"),
    "Data Science": ("turn data into insights that guide decisions", ["Analyse large datasets", "Build dashboards and reports", "Design and run experiments", "Present findings to stakeholders"], ["Strong SQL and Python or R", "Statistics fundamentals", "Data visualisation skills", "Attention to detail"], "BS in Statistics, Computer Science or related field"),
    "Mobile Development": ("create polished mobile apps for Android and iOS", ["Build and maintain mobile app features", "Integrate REST APIs", "Fix crashes and improve performance", "Publish releases to app stores"], ["Experience shipping a mobile app", "Understanding of mobile UI patterns", "Knowledge of REST APIs and JSON", "Git proficiency"], "BS Computer Science or equivalent"),
    "UI/UX Design": ("design intuitive, beautiful user experiences", ["Create wireframes, mockups and prototypes", "Run usability tests", "Maintain the design system", "Work closely with developers"], ["Portfolio of shipped design work", "Proficiency in Figma", "Understanding of usability principles", "Good communication skills"], "Degree in Design, HCI or related field"),
    "Cyber Security": ("protect systems and data from threats", ["Monitor systems for suspicious activity", "Run vulnerability assessments", "Respond to and document incidents", "Recommend security improvements"], ["Networking and OS fundamentals", "Knowledge of common vulnerabilities (OWASP)", "Experience with security tooling", "Analytical mindset"], "BS in Cyber Security, Computer Science or related field"),
    "DevOps": ("automate delivery and keep services reliable", ["Build and maintain CI/CD pipelines", "Manage infrastructure as code", "Monitor systems and respond to incidents", "Improve deployment reliability"], ["Linux administration", "Experience with Docker and CI/CD", "Scripting skills", "Understanding of monitoring tools"], "BS Computer Science or equivalent"),
    "Cloud Computing": ("build and operate secure cloud infrastructure", ["Design and deploy cloud resources", "Optimise cost and performance", "Implement security best practices", "Support engineering teams"], ["Hands-on cloud platform experience", "Networking fundamentals", "Infrastructure-as-code skills", "Problem-solving ability"], "BS Computer Science or equivalent"),
    "Digital Marketing": ("grow our audience and brand online", ["Plan and run digital campaigns", "Track and report campaign performance", "Create engaging content", "Optimise for search and conversions"], ["Experience with analytics tools", "Strong written communication", "Knowledge of social media platforms", "Creative thinking"], "Degree in Marketing, Business or related field"),
    "Accounting & Finance": ("keep our finances accurate and compliant", ["Maintain ledgers and reconcile accounts", "Prepare financial statements", "Support audits and tax filings", "Analyse budgets and variances"], ["Knowledge of accounting principles", "Proficiency in Excel", "Attention to detail", "Integrity and confidentiality"], "B.Com / BBA Finance or ACCA/CA (part-qualified)"),
    "Human Resources": ("support and grow our people", ["Coordinate recruitment and onboarding", "Maintain employee records", "Support performance reviews", "Answer employee queries"], ["Knowledge of HR practices", "Strong interpersonal skills", "Good organisation", "Confidentiality"], "Degree in HR, Business Administration or similar"),
    "Sales": ("win new customers and grow accounts", ["Identify and pursue leads", "Deliver product demos and proposals", "Meet monthly sales targets", "Maintain the CRM"], ["Excellent communication skills", "Target-driven attitude", "Negotiation skills", "Willingness to learn our product"], "Bachelor's degree in Business or related field"),
    "Customer Support": ("help customers succeed with our product", ["Answer customer tickets and calls", "Troubleshoot issues", "Document solutions", "Escalate complex problems"], ["Clear written and spoken English/Urdu", "Patience and empathy", "Basic technical aptitude", "Ability to multitask"], "Intermediate or Bachelor's degree"),
    "Project Management": ("deliver projects on time and within scope", ["Plan schedules and allocate resources", "Track progress and manage risks", "Run stand-ups and retrospectives", "Report to stakeholders"], ["Experience with Agile/Scrum", "Strong organisation", "Clear communication", "Familiarity with Jira or similar"], "Bachelor's degree; PMP/CSM is a plus"),
}

# (title, category, skills, salary multiplier, allowed levels)
L_ALL = ["fresh", "entry-level", "intermediate", "senior", "expert"]
L_MID = ["fresh", "entry-level", "intermediate", "senior"]
L_SEN = ["entry-level", "intermediate", "senior", "expert"]
ROLES = [
    ("Python Developer", "Software Development", "Python, Django, REST APIs, SQL, Git", 1.0, L_MID),
    ("Java Developer", "Software Development", "Java, Spring Boot, SQL, Git", 1.0, L_MID),
    ("Software Engineer", "Software Development", "Python, Data Structures, SQL, Git", 1.05, L_ALL),
    ("QA Automation Engineer", "Software Development", "Selenium, Python, Test Planning, CI", 0.85, L_MID),
    ("Django Developer", "Web Development", "Python, Django, PostgreSQL, REST APIs, HTML/CSS", 1.0, L_MID),
    ("Backend Developer", "Web Development", "Python, Node.js, SQL, REST APIs, Docker", 1.05, L_MID),
    ("Frontend Developer", "Web Development", "JavaScript, React, HTML, CSS, Git", 0.95, L_MID),
    ("Full Stack Developer", "Web Development", "Python, Django, JavaScript, React, SQL", 1.1, L_MID),
    ("React Developer", "Web Development", "React, JavaScript, TypeScript, REST APIs", 1.0, L_MID),
    ("WordPress Developer", "Web Development", "WordPress, PHP, HTML, CSS, SEO", 0.7, ["fresh", "entry-level", "intermediate"]),
    ("Machine Learning Engineer", "AI / Machine Learning", "Python, scikit-learn, PyTorch, SQL, MLOps", 1.3, L_MID),
    ("AI Engineer", "AI / Machine Learning", "Python, Deep Learning, LLMs, APIs, Docker", 1.35, L_MID),
    ("Computer Vision Engineer", "AI / Machine Learning", "Python, OpenCV, PyTorch, Deep Learning", 1.3, L_SEN),
    ("NLP Engineer", "AI / Machine Learning", "Python, NLP, Transformers, spaCy", 1.3, L_SEN),
    ("Data Scientist", "Data Science", "Python, Pandas, Statistics, SQL, Machine Learning", 1.2, L_MID),
    ("Data Analyst", "Data Science", "SQL, Excel, Power BI, Python, Statistics", 0.85, L_MID),
    ("Data Engineer", "Data Science", "Python, SQL, Airflow, Spark, Cloud", 1.2, L_SEN),
    ("BI Analyst", "Data Science", "SQL, Power BI, Tableau, Excel", 0.9, L_MID),
    ("Flutter Developer", "Mobile Development", "Flutter, Dart, REST APIs, Firebase", 0.95, L_MID),
    ("Android Developer", "Mobile Development", "Kotlin, Android SDK, REST APIs, Git", 1.0, L_MID),
    ("iOS Developer", "Mobile Development", "Swift, iOS SDK, REST APIs, Git", 1.05, L_MID),
    ("React Native Developer", "Mobile Development", "React Native, JavaScript, REST APIs", 1.0, L_MID),
    ("UI/UX Designer", "UI/UX Design", "Figma, Wireframing, Prototyping, User Research", 0.85, L_MID),
    ("Product Designer", "UI/UX Design", "Figma, Design Systems, User Research", 0.95, L_SEN),
    ("Graphic Designer", "UI/UX Design", "Photoshop, Illustrator, Branding", 0.7, ["fresh", "entry-level", "intermediate"]),
    ("Cyber Security Analyst", "Cyber Security", "Network Security, SIEM, Incident Response, Linux", 1.1, L_MID),
    ("Penetration Tester", "Cyber Security", "Kali Linux, Burp Suite, OWASP, Python", 1.15, L_SEN),
    ("SOC Analyst", "Cyber Security", "SIEM, Log Analysis, Threat Hunting", 1.0, L_MID),
    ("DevOps Engineer", "DevOps", "Docker, Kubernetes, CI/CD, Linux, Terraform", 1.2, L_MID),
    ("Site Reliability Engineer", "DevOps", "Linux, Kubernetes, Monitoring, Python", 1.25, L_SEN),
    ("Build & Release Engineer", "DevOps", "CI/CD, Git, Bash, Docker", 1.0, L_MID),
    ("Cloud Engineer", "Cloud Computing", "AWS, Azure, Terraform, Linux, Networking", 1.2, L_MID),
    ("Cloud Solutions Architect", "Cloud Computing", "AWS, Azure, Architecture, Security", 1.5, ["senior", "expert"]),
    ("Cloud Support Engineer", "Cloud Computing", "AWS, Linux, Troubleshooting, Networking", 0.9, ["fresh", "entry-level", "intermediate"]),
    ("Digital Marketing Specialist", "Digital Marketing", "SEO, Google Ads, Social Media, Analytics", 0.8, L_MID),
    ("SEO Specialist", "Digital Marketing", "SEO, Google Analytics, Content Strategy", 0.75, L_MID),
    ("Content Marketer", "Digital Marketing", "Copywriting, SEO, Social Media, Canva", 0.7, ["fresh", "entry-level", "intermediate"]),
    ("Social Media Manager", "Digital Marketing", "Social Media, Content Calendar, Analytics", 0.75, ["entry-level", "intermediate", "senior"]),
    ("Accountant", "Accounting & Finance", "Accounting, Excel, Tally, Taxation", 0.75, L_MID),
    ("Financial Analyst", "Accounting & Finance", "Financial Modelling, Excel, Budgeting, Reporting", 0.95, L_MID),
    ("Accounts Payable Officer", "Accounting & Finance", "Accounting, Excel, Invoicing", 0.65, ["fresh", "entry-level", "intermediate"]),
    ("HR Executive", "Human Resources", "Recruitment, HR Policies, Communication", 0.7, L_MID),
    ("Talent Acquisition Specialist", "Human Resources", "Sourcing, Interviewing, ATS, LinkedIn", 0.8, L_MID),
    ("HR Manager", "Human Resources", "HR Strategy, Employee Relations, Payroll", 1.1, ["senior", "expert"]),
    ("Sales Executive", "Sales", "Communication, Negotiation, CRM", 0.7, L_MID),
    ("Business Development Executive", "Sales", "Lead Generation, Negotiation, CRM, Presentations", 0.8, L_MID),
    ("Account Manager", "Sales", "Client Relations, CRM, Negotiation", 0.9, ["intermediate", "senior", "expert"]),
    ("Customer Support Officer", "Customer Support", "Communication, Ticketing, Problem Solving", 0.6, ["fresh", "entry-level", "intermediate"]),
    ("Technical Support Engineer", "Customer Support", "Troubleshooting, Networking, Communication, SQL", 0.75, L_MID),
    ("Customer Success Associate", "Customer Support", "Communication, CRM, Onboarding", 0.7, ["fresh", "entry-level", "intermediate"]),
    ("Project Manager", "Project Management", "Agile, Scrum, Jira, Communication", 1.15, ["intermediate", "senior", "expert"]),
    ("Scrum Master", "Project Management", "Scrum, Agile Coaching, Jira", 1.1, ["intermediate", "senior"]),
    ("Product Manager", "Project Management", "Roadmapping, Analytics, Agile, Communication", 1.3, ["intermediate", "senior", "expert"]),
]
ROLE_BY_TITLE = {r[0]: r for r in ROLES}

LEVEL_SALARY = {"fresh": (30000, 50000), "entry-level": (50000, 90000), "intermediate": (90000, 170000),
                "senior": (170000, 280000), "expert": (250000, 420000)}

CITIES = ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Gujranwala", "Sialkot"]

# name, industry, city, focus categories, employees, founded, blurb, phone
COMPANIES = [
    ("TechNova Solutions", "Software Development", "Lahore", ["Software Development", "Web Development", "Cloud Computing", "DevOps"], 220, 2014, "builds custom web platforms and enterprise software for clients across the region.", "+92 42 3555 0101"),
    ("CodeCraft Technologies", "Software Development", "Islamabad", ["Web Development", "Software Development", "Mobile Development"], 140, 2016, "is a product engineering studio focused on clean, maintainable code.", "+92 51 2555 0102"),
    ("AI Vision Labs", "Artificial Intelligence", "Islamabad", ["AI / Machine Learning", "Data Science"], 65, 2019, "researches and ships computer vision and language AI products.", "+92 51 2555 0103"),
    ("DataBridge Systems", "Data & Analytics", "Karachi", ["Data Science", "AI / Machine Learning", "Cloud Computing"], 110, 2015, "helps organisations unlock value from their data with modern analytics.", "+92 21 3555 0104"),
    ("CloudPeak Software", "Cloud Computing", "Lahore", ["Cloud Computing", "DevOps", "Cyber Security"], 95, 2017, "designs and operates cloud-native infrastructure for growing companies.", "+92 42 3555 0105"),
    ("DigitalWave Solutions", "Digital Marketing", "Karachi", ["Digital Marketing", "Sales", "UI/UX Design", "Customer Support"], 80, 2018, "is a full-service digital marketing and branding agency.", "+92 21 3555 0106"),
    ("NextGen Analytics", "Data & Analytics", "Rawalpindi", ["Data Science", "AI / Machine Learning", "Project Management"], 70, 2018, "provides business intelligence and predictive analytics services.", "+92 51 2555 0107"),
    ("SmartTech Pakistan", "Information Technology", "Faisalabad", ["Software Development", "Mobile Development", "Customer Support", "Project Management"], 180, 2012, "delivers IT services, mobile apps and managed support.", "+92 41 2555 0108"),
    ("InnovateSoft", "Software Development", "Multan", ["Software Development", "Web Development", "UI/UX Design", "Mobile Development"], 60, 2020, "is a young software house building web and mobile products.", "+92 61 4555 0109"),
    ("WebCore Technologies", "Web Development", "Lahore", ["Web Development", "UI/UX Design", "Digital Marketing"], 90, 2016, "creates fast, well-designed websites and web applications.", "+92 42 3555 0110"),
    ("SecureNet Systems", "Cyber Security", "Islamabad", ["Cyber Security", "DevOps", "Cloud Computing"], 55, 2017, "offers security testing, monitoring and consulting.", "+92 51 2555 0111"),
    ("FinEdge Consulting", "Finance & Consulting", "Karachi", ["Accounting & Finance", "Human Resources", "Sales", "Project Management"], 120, 2011, "provides finance, HR and management consulting to mid-sized firms.", "+92 21 3555 0112"),
]
FORCED = {"TechNova Solutions": ["Python Developer", "Django Developer"], "CodeCraft Technologies": ["Django Developer", "Full Stack Developer"],
          "AI Vision Labs": ["Machine Learning Engineer", "AI Engineer"], "DataBridge Systems": ["Data Scientist", "Data Analyst"]}

FIRST_M = ["Muhammad", "Usman", "Hamza", "Bilal", "Ahmed", "Hassan", "Talha", "Faisal", "Zain", "Saad", "Imran", "Kamran"]
FIRST_F = ["Ayesha", "Fatima", "Sana", "Hina", "Maryam", "Zainab", "Noor", "Areeba", "Iqra", "Sadia", "Mahnoor", "Laiba"]
LAST = ["Ali", "Khan", "Ahmed", "Raza", "Malik", "Sheikh", "Butt", "Qureshi", "Siddiqui", "Chaudhry", "Hussain", "Iqbal", "Mirza", "Javed", "Farooq"]

# name, username, title, category track, skills, years
SEEKERS = [
    ("Muhammad Ali", "demo_seeker", "Software Developer", ["Software Development", "Web Development"], "Python, Django, SQL, Git, REST APIs", 2),
    ("Ayesha Khan", "ayesha.khan", "Data Scientist", ["Data Science", "AI / Machine Learning"], "Python, Pandas, Machine Learning, SQL, Statistics", 3),
    ("Usman Ahmed", "usman.ahmed", "Web Developer", ["Web Development", "Software Development"], "JavaScript, React, HTML, CSS, Node.js", 2),
    ("Sana Malik", "sana.malik", "UI/UX Designer", ["UI/UX Design"], "Figma, Wireframing, Prototyping, User Research", 3),
    ("Hamza Raza", "hamza.raza", "Machine Learning Engineer", ["AI / Machine Learning", "Data Science"], "Python, PyTorch, scikit-learn, Deep Learning", 4),
    ("Fatima Sheikh", "fatima.sheikh", "Digital Marketer", ["Digital Marketing", "Sales"], "SEO, Google Ads, Social Media, Analytics", 2),
    ("Bilal Butt", "bilal.butt", "DevOps Engineer", ["DevOps", "Cloud Computing"], "Docker, Kubernetes, CI/CD, Linux, AWS", 5),
    ("Maryam Qureshi", "maryam.qureshi", "Accountant", ["Accounting & Finance"], "Accounting, Excel, Taxation, Tally", 3),
    ("Talha Siddiqui", "talha.siddiqui", "Flutter Developer", ["Mobile Development"], "Flutter, Dart, Firebase, REST APIs", 2),
    ("Zainab Chaudhry", "zainab.chaudhry", "HR Executive", ["Human Resources"], "Recruitment, HR Policies, Communication", 3),
    ("Hassan Hussain", "hassan.hussain", "Cyber Security Analyst", ["Cyber Security"], "Network Security, SIEM, Linux, OWASP", 3),
    ("Noor Iqbal", "noor.iqbal", "Frontend Developer", ["Web Development", "UI/UX Design"], "React, JavaScript, CSS, TypeScript", 1),
    ("Faisal Mirza", "faisal.mirza", "Sales Executive", ["Sales", "Customer Support"], "Negotiation, CRM, Communication", 4),
    ("Areeba Javed", "areeba.javed", "Data Analyst", ["Data Science"], "SQL, Excel, Power BI, Python", 1),
    ("Saad Farooq", "saad.farooq", "Cloud Engineer", ["Cloud Computing", "DevOps"], "AWS, Terraform, Linux, Networking", 4),
    ("Iqra Ali", "iqra.ali", "Project Manager", ["Project Management"], "Agile, Scrum, Jira, Communication", 6),
    ("Kamran Khan", "kamran.khan", "Customer Support Officer", ["Customer Support"], "Communication, Ticketing, Problem Solving", 1),
    ("Mahnoor Raza", "mahnoor.raza", "AI Engineer", ["AI / Machine Learning", "Software Development"], "Python, LLMs, Deep Learning, APIs, Docker", 2),
]
EDU = ["BS Computer Science, FAST-NUCES (fictional)", "BS Software Engineering, Punjab Tech University (fictional)", "BBA, Lahore Business Institute (fictional)",
       "BS Data Science, Islamabad Institute of Technology (fictional)", "B.Com, Karachi Commerce College (fictional)"]
COVER = ["I am excited to apply for the {t} position at {c}. My background in {s} matches the role well, and I would love to contribute to your team.",
         "Please accept my application for {t}. I have hands-on experience with {s} and I am eager to grow with {c}.",
         "With {y} year(s) of experience in {s}, I believe I can add value as your next {t}. Thank you for considering my application."]
STATUS_W = [("pending", 35), ("reviewed", 25), ("shortlisted", 20), ("rejected", 12), ("accepted", 8)]
PALETTE = [(15, 91, 107), (32, 76, 128), (94, 53, 140), (168, 74, 40), (46, 110, 72), (150, 60, 90), (60, 70, 90), (196, 120, 20)]


def make_pdf(title, lines):
    """Build a tiny valid one-page PDF without any third-party library."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    wrapped = []
    for ln in lines:
        wrapped += textwrap.wrap(ln, 88) or [""]
    body = ["BT", "/F1 20 Tf", "50 790 Td", f"({esc(title)}) Tj", "/F1 11 Tf", "0 -30 Td", "16 TL"]
    body += [f"({esc(l)}) '" for l in wrapped[:42]]
    body.append("ET")
    stream = "\n".join(body).encode("latin-1", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def make_logo(path, initials, colour):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (256, 256), colour)
    d = ImageDraw.Draw(img)
    d.ellipse((150, -60, 330, 120), fill=tuple(min(255, c + 40) for c in colour))
    d.rectangle((0, 214, 256, 256), fill=tuple(max(0, c - 35) for c in colour))
    try:
        font = ImageFont.load_default(size=96)
    except TypeError:
        font = ImageFont.load_default()
    box = d.textbbox((0, 0), initials, font=font)
    d.text(((256 - (box[2] - box[0])) / 2 - box[0], (214 - (box[3] - box[1])) / 2 - box[1]), initials, fill="white", font=font)
    img.save(path, "PNG")


class Command(BaseCommand):
    help = "Create realistic fictional demo data (users, companies, jobs, applications, saved jobs)."

    def add_arguments(self, parser):
        parser.add_argument("--refresh-deadlines", action="store_true",
                            help="Push deadlines of active demo jobs into the future (useful if you seeded long ago).")

    @transaction.atomic
    def handle(self, *args, **opts):
        now, today = timezone.now(), timezone.localdate()
        pw = make_password(DEMO_PASSWORD)
        for sub in ("cvs", "company_logos", "profile_pictures"):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, sub), exist_ok=True)

        cats = {}
        for name, icon in CATEGORIES:
            cats[name] = Category.objects.get_or_create(name=name, defaults={"icon": icon, "description": f"Jobs in {name}"})[0]

        User.objects.get_or_create(username="demo_admin", defaults={
            "email": "admin@example.com", "first_name": "Demo", "last_name": "Admin", "password": pw,
            "is_staff": True, "is_superuser": True})

        # ---- companies + employers ----
        companies = []
        for i, (name, industry, city, focus, emp, year, blurb, phone) in enumerate(COMPANIES):
            username = "demo_employer" if i == 0 else f"employer_{name.split()[0].lower()}"
            first = (FIRST_M + FIRST_F)[(i * 5) % 24]
            last = LAST[(i * 3) % len(LAST)]
            user, _ = User.objects.get_or_create(username=username, defaults={
                "email": f"hr@{name.split()[0].lower()}.example", "first_name": first, "last_name": last, "password": pw})
            ep, _ = EmployerProfile.objects.get_or_create(user=user, defaults={"position": "Hiring Manager", "phone": phone})
            slug_domain = name.lower().replace(" ", "")
            company, created = Company.objects.get_or_create(name=name, defaults={
                "employer": ep, "industry": industry, "location": city, "employee_count": emp, "founded_year": year,
                "description": f"{name} {blurb} Founded in {year}, we are a team of about {emp} people based in {city}. "
                               f"(Fictional company created for demo purposes.)",
                "website": f"https://www.{slug_domain}.example", "email": f"careers@{slug_domain}.example", "phone": phone,
                "linkedin_url": f"https://www.linkedin.com/company/{slug_domain}-demo"})
            if not company.logo:
                fname = f"company_logos/{company.slug}.png"
                make_logo(os.path.join(settings.MEDIA_ROOT, fname), company.initials, PALETTE[i % len(PALETTE)])
                company.logo.name = fname
                company.save(update_fields=["logo"])
            companies.append((company, focus, i))

        # ---- jobs ----
        for company, focus, i in companies:
            pool = [r for r in ROLES if r[1] in focus]
            forced = [ROLE_BY_TITLE[t] for t in FORCED.get(company.name, [])]
            rest = [r for r in pool if r not in forced]
            chosen = forced + random.Random("roles-" + company.name).sample(rest, 6 + i % 3 - len(forced))
            for role_idx, (title, cat, skills, mult, levels) in enumerate(chosen):
                rng = random.Random(f"job-{company.name}-{title}")   # per-job generator => reruns are identical
                level = rng.choice(levels)
                lo, hi = LEVEL_SALARY[level]
                smin = int(round(lo * mult * rng.uniform(0.9, 1.1) / 5000) * 5000)
                smax = int(round(hi * mult * rng.uniform(0.9, 1.1) / 5000) * 5000)
                smax = max(smax, smin + 20000)
                if level == "fresh":
                    jtype = rng.choice(["internship", "full-time", "full-time"])
                elif level in ("senior", "expert"):
                    jtype = rng.choice(["full-time", "full-time", "contract"])
                else:
                    jtype = rng.choice(["full-time", "full-time", "full-time", "part-time", "contract", "freelance"])
                if jtype == "internship":
                    smin, smax = 25000, 45000
                is_remote = jtype == "remote" or rng.random() < 0.2
                location = "Remote" if is_remote and rng.random() < 0.5 else (
                    company.location if rng.random() < 0.65 else rng.choice(CITIES))
                r = rng.random()
                if role_idx == 0 and company.name in FORCED:
                    r = 0.5                        # always keep the showcase jobs active
                if r < 0.06:
                    status, deadline, age = "draft", today + datetime.timedelta(days=rng.randint(10, 40)), rng.randint(1, 10)
                elif r < 0.14:
                    status, deadline, age = "closed", today + datetime.timedelta(days=rng.randint(-5, 20)), rng.randint(10, 50)
                elif r < 0.20:
                    status, deadline, age = "active", today - datetime.timedelta(days=rng.randint(1, 10)), rng.randint(20, 60)
                else:
                    status, deadline, age = "active", today + datetime.timedelta(days=rng.randint(3, 75)), rng.randint(0, 40)
                featured = rng.random() < 0.15 or (role_idx == 0 and company.name in FORCED)
                summary, resp, req, edu = CAT_TEXT[cat]
                exp_txt = {"fresh": "Fresh graduates are welcome to apply.", "entry-level": "0-2 years of experience.",
                           "intermediate": "2-5 years of experience.", "senior": "5+ years of experience.",
                           "expert": "8+ years of experience and a record of leading work."}[level]
                description = (f"{company.name} is hiring a {title} in {location} to {summary}. "
                               f"You will join a friendly team and work on real projects from day one.\n\n{exp_txt}")
                vacancies, hours = rng.randint(1, 4), rng.randint(0, 20)
                job, created = Job.objects.get_or_create(company=company, title=title, defaults={
                    "category": cats[cat], "description": description, "responsibilities": "\n".join(resp),
                    "requirements": "\n".join(req + [exp_txt]), "skills_required": skills,
                    "education_required": edu, "salary_min": smin, "salary_max": smax, "location": location,
                    "job_type": jtype, "experience_level": level, "is_remote": is_remote, "is_featured": featured,
                    "deadline": deadline, "status": status, "vacancies": vacancies})
                if created:
                    Job.objects.filter(pk=job.pk).update(created_at=now - datetime.timedelta(days=age, hours=hours))
                elif opts["refresh_deadlines"] and job.status == "active":
                    job.deadline = today + datetime.timedelta(days=rng.randint(10, 60))
                    job.save(update_fields=["deadline", "updated_at"])
        Job.objects.expire_overdue()

        # ---- job seekers ----
        seekers = []
        for n, (full, username, title, tracks, skills, years) in enumerate(SEEKERS):
            first, last = full.split(" ", 1)
            rng = random.Random("seeker-" + username)
            user, _ = User.objects.get_or_create(username=username, defaults={
                "email": f"{username.replace('.', '_')}@example.com", "first_name": first, "last_name": last, "password": pw})
            profile, _ = JobSeekerProfile.objects.get_or_create(user=user, defaults={
                "phone": f"+92 300 555{n:04d}", "location": rng.choice(CITIES), "professional_title": title,
                "bio": f"{title} with {years} year(s) of experience. Passionate about learning and building useful things. (Fictional profile.)",
                "skills": skills, "education": rng.choice(EDU),
                "experience": f"{years} year(s) as {title} at a fictional software company.",
                "years_of_experience": years, "expected_salary": 30000 + years * 25000 + rng.randint(0, 4) * 5000,
                "preferred_location": rng.choice(CITIES), "github": f"https://github.com/{username.replace('.', '-')}-demo",
                "linkedin": f"https://www.linkedin.com/in/{username.replace('.', '-')}-demo"})
            if not profile.cv:
                fname = f"cvs/{username.replace('.', '_')}_cv.pdf"
                pdf = make_pdf(f"{full} - {title} CV", [
                    "FICTIONAL DEMO CV - not a real person.", "", f"Email: {user.email}   Phone: {profile.phone}",
                    f"Location: {profile.location}", "", "PROFILE", profile.bio, "", "SKILLS", skills, "",
                    "EDUCATION", profile.education, "", "EXPERIENCE", profile.experience])
                with open(os.path.join(settings.MEDIA_ROOT, fname), "wb") as fh:
                    fh.write(pdf)
                profile.cv.name = fname
                profile.save(update_fields=["cv"])
            seekers.append((user, profile, tracks, years, n == 0))

        # ---- applications + saved jobs ----
        open_jobs = list(Job.objects.open().select_related("category", "company").order_by("id"))
        for user, profile, tracks, years, is_demo in seekers:
            rng = random.Random("activity-" + user.username)
            matching = [j for j in open_jobs if j.category.name in tracks]
            n_apps = 8 if is_demo else rng.randint(3, 8)
            picks, seen = [], set()
            while len(picks) < n_apps:
                pool = matching if (matching and rng.random() < 0.7) else open_jobs
                j = rng.choice(pool)
                if j.pk not in seen:
                    seen.add(j.pk)
                    picks.append(j)
            for job in picks:
                status = rng.choices([s for s, _ in STATUS_W], [w for _, w in STATUS_W])[0]
                ago = min(rng.randint(0, 25), max(0, (now - job.created_at).days))
                letter = rng.choice(COVER).format(t=job.title, c=job.company.name, s=job.skills_list[0] if job.skills_list else "this field", y=years)
                hrs = rng.randint(0, 12)
                app, created = Application.objects.get_or_create(job=job, applicant=user, defaults={
                    "full_name": user.get_full_name(), "email": user.email, "phone": profile.phone,
                    "cover_letter": letter, "status": status})
                if created:
                    app.cv.name = profile.cv.name
                    app.save(update_fields=["cv"])
                    Application.objects.filter(pk=app.pk).update(created_at=now - datetime.timedelta(days=ago, hours=hrs))
            saved = rng.sample(open_jobs, 6 if is_demo else rng.randint(2, 7))
            for job in saved:
                SavedJob.objects.get_or_create(user=user, job=job)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        for label, qs in [("Users", User.objects.all()), ("Job seekers", JobSeekerProfile.objects.all()),
                          ("Employers", EmployerProfile.objects.all()), ("Companies", Company.objects.all()),
                          ("Categories", Category.objects.all()), ("Jobs", Job.objects.all()),
                          ("Applications", Application.objects.all()), ("Saved jobs", SavedJob.objects.all())]:
            self.stdout.write(f"  {label:<13}{qs.count()}")
        self.stdout.write(f"Demo password for all demo accounts: {DEMO_PASSWORD}")
        self.stdout.write("Logins: demo_seeker, demo_employer, demo_admin")
