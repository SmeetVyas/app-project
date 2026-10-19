# API Sentinel 🛡️
### *Full-Stack API Testing, Monitoring, and Quality Assurance Platform for Developers*

![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)
![Django 6.1](https://img.shields.io/badge/Django-6.1.2-green.svg)
![Pytest](https://img.shields.io/badge/Tests-47%20Passed-brightgreen.svg)
![Security](https://img.shields.io/badge/SSRF%20Guard-Strict%20Enforced-red.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

---

## 📌 Project Overview
**API Sentinel** is a professional, production-minded full-stack web application built with **Python 3.13**, **Django 6.1**, vanilla modern JavaScript, and Chart.js. Inspired by developer ergonomics in tools like Postman and Datadog, API Sentinel allows engineering teams to organize API endpoints, execute interactive HTTP requests, configure multi-criteria automated assertions, execute regression test suites, track latency telemetry, monitor endpoint availability with automated failure alerting, and export sanitized audit reports to CSV and publication-ready PDF documents.

This project was built to satisfy real-world production QA and developer tool standards as a flagship **Python Developer Internship Portfolio Project**.

---

## 🚀 Key Features

### 1. 🔐 Tenant Isolation & Authentication
- Full user registration, login, logout, and password security using Django's authentication system.
- Strict multi-tenant isolation: Developers can only view, execute, modify, or export projects, endpoints, and test results that belong to them.
- Session-based CSRF protection, secure cookie handling, and comprehensive user audit logging.

### 2. 🗂️ Project & Workspace Management
- Group APIs into microservice or client project workspaces.
- Real-time database-backed dashboard metrics: Endpoint count, automated test runs, pass/fail ratios, and mean latency computed live via the Django ORM.

### 3. ⚡ Interactive API Request Builder (Playground)
- Send real-time `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, and `HEAD` requests.
- Dynamic key-value row editors for URL query parameters and custom HTTP headers.
- Built-in JSON request body editor with auto-formatting (`Format JSON`) and syntax validation.
- Live response inspector displaying accurate HTTP status codes, latency in milliseconds, content size, formatted JSON body with syntax highlighting, and raw response headers.
- One-click **"Copy Response"** and **"Save as Endpoint"** workflows.

### 4. 🛡️ Enterprise-Grade SSRF Protection & Security
Outbound request testing is treated as a sensitive security capability:
- **Bulletproof IP Validation:** Blocks all loopback (`127.0.0.1`, `::1`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and multicast/unspecified ranges.
- **Cloud Metadata Defense:** Explicitly blocks cloud provider metadata IP endpoints (`169.254.169.254`, `100.100.100.200`, `192.0.0.192`, `metadata.google.internal`).
- **DNS Resolution Pre-flight:** Performs pre-flight DNS lookups and checks every candidate IPv4/IPv6 address prior to connection establishment.
- **Redirect Controls:** Outbound redirects are disabled by default; any followed redirects re-validate candidate destinations against the SSRF guard.
- **Secret Redaction & At-Rest Encryption:** API keys, Bearer tokens, and basic auth passwords are encrypted at rest using AES-CBC with authenticated HMAC (Fernet) and automatically masked (`sk_l••••4a9f`) in UI displays, logs, and exported reports.

### 5. 🧪 Automated Test Engine & Declarative Assertions
- Build reusable Test Suites composed of ordered Test Cases.
- Multi-criteria declarative assertion engine:
  - **Expected Status Code:** Exact equality (e.g. `200`) or status lists (e.g. `200, 201, 204`).
  - **Maximum Response Time:** Enforce strict latency SLA thresholds in milliseconds (e.g. `<= 500ms`).
  - **Content-Type Validation:** Substring verification (e.g. `application/json`).
  - **JSON Property Exists:** Dot-notation path inspection (e.g. `user.profile.id` or `items[0].sku`).
  - **JSON Value Equality:** Type-coerced validation (`number`, `string`, `boolean`, `null`).
  - **JSON Value Type:** Enforce schema types (`string`, `number`, `boolean`, `array`, `object`).
  - **Body Text & Regex:** Substring search and regular expression pattern matching.
  - **Header Checks:** Header existence and exact header value verification.
- **Zero Insecure Code Execution:** Evaluates all rules via safe AST parsing and deterministic logic. **Never** runs user-submitted Python via `eval()`, `exec()`, or shell commands.

### 6. 📊 Regression Analyzer & Performance Comparisons
- Compare any two historical test runs (Baseline vs. Comparison).
- Automatically flags:
  - **Functional Regressions:** Tests that previously passed in baseline but failed in the comparison run.
  - **Resolved Fixes:** Tests that previously failed and are now passing.
  - **Performance Spikes:** Detects and flags latency degradations (e.g. `> 25%` and `> 50ms` increase).
  - **Pass Rate Delta:** Quantifies the net quality change between releases.

### 7. ⏱️ Scheduled Monitoring & Automated Failure Alerts
- Configure scheduled health checks at intervals (5 min, 15 min, 30 min, 1 hour, 6 hours, 24 hours).
- Safe, non-blocking management command: `python manage.py run_monitor` (supports single execution or continuous daemon mode with `--loop`).
- Telemetry logs recorded for every check with uptime percentage tracking.
- Automated email alert dispatch on health check failures (configurable via SMTP in `.env`).

### 8. 📄 Reports & Data Exports
- **CSV Export:** Instant sanitized CSV download of any test execution run.
- **PDF Reports:** Audit-ready PDF generated directly in memory via **ReportLab**, featuring executive summary cards, pass/fail totals, latency measurements, and confidentiality notices.

### 9. 🎨 Premium Developer SaaS UI
- Clean, responsive dashboard designed for desktop, tablet, and mobile.
- Elegant **Light and Dark themes** with instant toggling and `localStorage` persistence.
- Reusable components: Method badges (GET, POST, PUT, PATCH, DELETE), status pills, tabs, interactive modals, and auto-dismissing toast notifications.
- Integrated **Chart.js** analytics: Response-time trends over time and pass/fail distribution donuts.

---

## 🏗️ Architecture & Tech Stack

```mermaid
flowchart TD
    User([Developer / Browser]) -->|HTTP / HTML5| DjangoApp[Django 6.1 Web App]
    DjangoApp -->|Auth & Ownership| ORM[(SQLite / PostgreSQL)]
    DjangoApp -->|Pre-flight SSRF Guard| SSRFService[SSRF Guard / DNS Resolver]
    SSRFService -->|Allowed Public IP| HttpClient[Outbound HTTP Client]
    SSRFService -.->|Blocked Private/Metadata IP| ErrorBlock[SSRF Security Error]
    HttpClient -->|Outbound HTTP/S| ExternalAPI[Target Public REST API]
    ExternalAPI -->|Status, Headers, Body| AssertionEngine[Declarative Assertion Engine]
    AssertionEngine -->|Persist Metrics| TestResults[(TestRun / TestResult Models)]
    TestResults -->|Render Telemetry| Dashboard[Chart.js / Analytics Dashboard]
    TestResults -->|Export| PDFEngine[ReportLab PDF / CSV Exporter]
    CronDaemon[Management Command: run_monitor] -->|Periodic Trigger| HttpClient
```

### Verified Dependencies (Python 3.13 Compatible)
| Package | Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.13.15` | Core runtime |
| **Django** | `6.1.2` | Web platform, ORM, migrations, and session auth |
| **requests** | `2.34.2` | Controlled outbound HTTP communication |
| **cryptography** | `50.0.2` | Fernet symmetric AES encryption for secret keys & tokens |
| **reportlab** | `5.0.1` | Audit-ready PDF report generation |
| **pytest** | `9.1.1` | Unit and integration testing framework |
| **pytest-django** | `4.14.0` | Pytest fixtures and test database integration |
| **python-dotenv** | `1.2.4` | Environment variable management |
| **Chart.js** | `4.4.1` (CDN) | Interactive dashboard charts |

---

## 📂 Project Directory Structure

```
apisentinel/
├── manage.py
├── pytest.ini
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── apisentinel/                    # Master Project Settings & Routing
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/                           # Auth, Projects, Dashboard & Settings
│   ├── models.py                   # Project & AuditLog
│   ├── forms.py                    # UserRegisterForm & ProjectForm
│   ├── views.py                    # Dashboard, Project CRUD, Login/Register
│   ├── context_processors.py       # Global project selector context
│   └── urls.py
├── endpoints/                      # Endpoint Management & Request Builder
│   ├── models.py                   # Endpoint & SecureCredential
│   ├── forms.py                    # EndpointForm with SSRF checks
│   ├── views.py                    # Endpoint CRUD, Request Builder AJAX API
│   └── urls.py
├── testing_engine/                 # Test Engine, Suites, Cases & Regressions
│   ├── models.py                   # TestSuite, TestCase, Assertion, TestRun, TestResult
│   ├── forms.py                    # TestSuiteForm, TestCaseForm, AssertionForm
│   ├── views.py                    # Suite CRUD, Runner, History, Regression Analyzer
│   └── urls.py
├── monitoring/                     # Health Checks & Scheduled Monitoring
│   ├── models.py                   # MonitorSchedule & MonitorCheckLog
│   ├── forms.py                    # MonitorScheduleForm
│   ├── views.py                    # Monitor views & toggle
│   ├── urls.py
│   └── management/
│       └── commands/
│           ├── run_monitor.py      # Background monitor executor
│           └── seed_demo_data.py   # Complete demonstration seed script
├── analytics/                      # Metrics & Reporting
│   ├── views.py                    # QA Analytics, CSV & ReportLab PDF exports, API docs
│   └── urls.py
├── services/                       # Reusable Business Logic
│   ├── __init__.py
│   ├── ssrf_guard.py               # Bulletproof SSRF protection & IP validator
│   ├── http_client.py              # Controlled outbound request client with redaction
│   ├── assertion_engine.py         # Multi-rule declarative assertion evaluator
│   ├── crypto_service.py           # Fernet encryption & secret masking
│   ├── test_runner.py              # Suite execution orchestrator
│   ├── regression_service.py       # Run diff analyzer (functional & latency deltas)
│   └── pdf_generator.py            # ReportLab styled PDF report generator
├── static/
│   ├── css/
│   │   └── style.css               # Responsive Light/Dark theme CSS variables
│   └── js/
│       ├── app.js                  # Theme toggling, toast notifications, clipboard
│       ├── request_builder.js      # Interactive API playground AJAX engine
│       └── dashboard_charts.js     # Chart.js renderers
├── templates/                      # Reusable Django Templates
│   ├── base.html                   # Master layout with sidebar & topbar
│   ├── auth/                       # Login and registration templates
│   ├── dashboard/                  # Overview metrics & Chart.js widgets
│   ├── projects/                   # Project list, detail, and forms
│   ├── endpoints/                  # Endpoints list, form, and Request Builder
│   ├── testing/                    # Suite detail, runs, history, regression diff
│   ├── monitoring/                 # Health check schedules and logs
│   ├── analytics/                  # Telemetry analytics
│   ├── docs/                       # Internal API reference
│   └── settings/                   # Security status and audit logs
└── tests/                          # 47 Unit & Integration Pytest Tests
    ├── conftest.py
    ├── test_ssrf_guard.py
    ├── test_crypto_service.py
    ├── test_assertion_engine.py
    ├── test_http_client.py
    ├── test_projects.py
    ├── test_endpoints.py
    ├── test_test_engine.py
    ├── test_monitoring.py
    └── test_reports.py
```

---

## 🛠️ Local Installation & Setup

### 1. Prerequisites
- **Python 3.13** installed on your system.
- Git.

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/api-sentinel.git
cd api-sentinel
```

### 3. Create and Activate a Virtual Environment
```bash
# On Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(On Windows: `Copy-Item .env.example .env`)*

A default development `FIELD_ENCRYPTION_KEY` is provided in `.env.example`. You can generate a custom 32-byte key anytime with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 6. Run Database Migrations
```bash
python manage.py migrate
```

### 7. Seed Demonstration Data (Recommended)
Populates realistic demo microservices, endpoints, assertions, historical runs, and monitor logs:
```bash
python manage.py seed_demo_data
```
> **Default Demo Login:**
> - **Username:** `demo_user`
> - **Password:** `SentinelPass2026!`

### 8. Start the Development Server
```bash
python manage.py runserver
```
Visit **`http://127.0.0.1:8000/`** in your browser.

---

## 🧪 Running the Automated Test Suite

API Sentinel includes 47 unit and integration tests covering SSRF guards, cryptographic security, declarative rule evaluations, tenant isolation, mocked outbound HTTP calls, regression detection, and PDF generation.

Run all tests via pytest:
```bash
pytest
```

Run with verbose test names and coverage summary:
```bash
pytest -v
```

---

## ⏰ Background Scheduled Monitoring

API Sentinel provides a safe, standalone management command for health check automation that can run as a cron job or background worker process:

```bash
# Run a single check cycle for all due monitors:
python manage.py run_monitor

# Run continuously as a background daemon (checking every 30 seconds):
python manage.py run_monitor --loop --sleep 30
```

---

## 🚢 Production Deployment Recommendations

1. **WSGI Server:** Use **Gunicorn** or **Uvicorn** behind an **Nginx** reverse proxy:
   ```bash
   gunicorn apisentinel.wsgi:application --bind 0.0.0.0:8000 --workers 3
   ```
2. **Database:** Switch from SQLite to PostgreSQL by providing the `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/apisentinel_prod
   ```
3. **Static Collection:** Run `python manage.py collectstatic --noinput` to bundle static CSS and JS.
4. **Environment Hardening:** Set `DJANGO_DEBUG=False`, configure valid `DJANGO_ALLOWED_HOSTS`, and set secure secret keys.

---

## 🎓 Learning Takeaways for IT Students
- **Separation of Concerns:** Notice how outbound network execution (`services/http_client.py`), security validation (`services/ssrf_guard.py`), rule evaluation (`services/assertion_engine.py`), and storage (`models.py`) are strictly decoupled.
- **Why No `eval()`?** Never evaluate user input as Python code. Using structured dictionary traversal (`data['key']['subkey']`) is 100% immune to remote code execution (RCE).
- **At-Rest Secret Security:** API tokens are encrypted in the database using Fernet symmetric encryption. If the database file is ever exposed, raw API credentials cannot be recovered without the encryption key.

---

## ⚖️ Known Limitations & Future Enhancements
- **Multi-region Agents:** Scheduled monitors currently execute from the host server. A future enhancement could support distributed execution from multiple geographic regions (AWS us-east, eu-west, ap-south).
- **OAuth 2.0 Flow:** Currently supports Bearer tokens, API Keys, and Custom Headers. A future update could add full OAuth2 client credential refresh flows.
- **WebSocket Testing:** Extensible to test real-time WebSocket and gRPC endpoints.

---

*Developed with pride as a production-minded Python Developer Portfolio Project.*
