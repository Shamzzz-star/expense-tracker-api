# Expense Tracker API

![tests](https://github.com/Shamzzz-star/expense-tracker-api/actions/workflows/tests.yml/badge.svg)

A REST API for tracking personal expenses, built with **Django REST Framework**, **PostgreSQL** and **JWT authentication**.
Users can organise expenses into categories with optional monthly budgets, filter and search their history,
see monthly and yearly spending reports, and export their data to CSV.

## Features

- **JWT auth**: register, log in, refresh tokens (`djangorestframework-simplejwt`)
- **Per-user data isolation**: every query is scoped to the logged-in user, so other users' data returns 404
- **Categories** with optional monthly budgets and case-insensitive unique names per user
- **Expenses**: full CRUD with validation (positive amounts, only your own categories)
- **Filtering, search, ordering and pagination**: by date range, category and amount range
- **Reports**
  - `GET /api/expenses/summary/?month=YYYY-MM`: monthly total, per-category breakdown, over-budget flags
  - `GET /api/expenses/trend/?year=YYYY`: totals for each month of the year
- **CSV export** of filtered expenses
- **Web frontend** at `/`: sign in, add and edit expenses and categories, budget bars, monthly trend chart, filters and CSV export
- **Interactive API docs** (OpenAPI / Swagger) via `drf-spectacular`
- **Security**: debug off by default, required secret key, rate-limited login and sign-up, CSV formula-injection protection, optional HTTPS hardening
- **Test suite** with `pytest` + `pytest-django`, at about 97% coverage
- **Docker Compose** setup (API + PostgreSQL) and **GitHub Actions** CI

## Tech stack

Python 3.12 · Django · Django REST Framework · PostgreSQL · SimpleJWT · django-filter · drf-spectacular · pytest · Docker · Gunicorn

## Project structure

```
config/          Django settings and root URLs
accounts/        Registration, JWT login, current-user endpoint
expenses/
  models.py      Category and Expense models
  serializers.py Validation and representation
  filters.py     Date / amount / category filters
  services.py    Reporting queries (monthly summary, yearly trend)
  views.py       ViewSets, report and export endpoints
frontend/        Web UI (one page plus static JS/CSS) served at /
tests/           pytest test suite
```

## Getting started

### Option 1: Docker (API + PostgreSQL)

```bash
cp .env.example .env             # then set DJANGO_SECRET_KEY to a long random string
docker compose up --build
```

The app runs at http://localhost:8000 and the API docs at http://localhost:8000/api/docs/.

### Option 2: Local (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # keeps DJANGO_DEBUG=True for local use
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the web app.

### Configuration

Settings come from environment variables or `.env` (see `.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `False` | Debug pages. Turn on only for local development. |
| `DJANGO_SECRET_KEY` | none | Required whenever debug is off. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Host names the site answers to. |
| `DJANGO_ADMIN_URL` | `admin/` | Path of the Django admin. |
| `DJANGO_AUTH_RATE` | `10/min` | Login, refresh and sign-up attempts allowed per IP. |
| `DJANGO_HTTPS` | `False` | When served over HTTPS: secure cookies, HSTS and redirect to https. |
| `DJANGO_BEHIND_PROXY` | `False` | Trust `X-Forwarded-Proto` from a reverse proxy (with `DJANGO_HTTPS`). |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | none | Extra trusted origins for the admin, e.g. `https://example.com`. |

### Run the tests

```bash
pytest --cov=expenses --cov=accounts
```

## API overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Create an account |
| POST | `/api/auth/token/` | Log in and get `access` + `refresh` tokens |
| POST | `/api/auth/token/refresh/` | Get a new access token |
| GET | `/api/auth/me/` | Current user |
| GET / POST | `/api/categories/` | List / create categories |
| GET / PUT / PATCH / DELETE | `/api/categories/{id}/` | Manage a category |
| GET / POST | `/api/expenses/` | List / create expenses |
| GET / PUT / PATCH / DELETE | `/api/expenses/{id}/` | Manage an expense |
| GET | `/api/expenses/summary/?month=2026-10` | Monthly report |
| GET | `/api/expenses/trend/?year=2026` | Month-by-month totals |
| GET | `/api/expenses/export/` | CSV download (accepts the same filters as the list) |

**List filters:** `date_from`, `date_to`, `category`, `min_amount`, `max_amount`, `search`, `ordering` (e.g. `-amount`), `page`

### Example

```bash
# Register and log in
curl -X POST localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "S3cure-pass!"}'
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token/ -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "S3cure-pass!"}' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

# Create a category and an expense
curl -X POST localhost:8000/api/categories/ -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" -d '{"name": "Food", "monthly_budget": "300.00"}'
curl -X POST localhost:8000/api/expenses/ -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" -d '{"amount": "12.50", "date": "2026-10-01", "category": 1, "description": "Lunch"}'

# Monthly summary
curl localhost:8000/api/expenses/summary/?month=2026-10 -H "Authorization: Bearer $TOKEN"
```

```json
{
  "month": "2026-10",
  "total": "12.50",
  "count": 1,
  "by_category": [
    {"category_id": 1, "category": "Food", "total": "12.50", "count": 1, "budget": "300.00", "over_budget": false}
  ]
}
```
