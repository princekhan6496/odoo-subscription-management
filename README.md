# Brightloop Subscription Management System

Brightloop is a modular full-stack subscription operations application based on the supplied Odoo Hackathon problem statement. It centralizes customer accounts, catalogue, plans, quotations, subscriptions, recurring billing, invoices, payments and reporting.

## Stack

- Frontend: Next.js 16.4, React 19.3, TypeScript, Tailwind CSS, Lucide.
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.1, Alembic, PostgreSQL.
- Security: Argon2 password hashing, short-lived JWT in HTTP-only cookies, double-submit CSRF protection, backend role checks, customer record isolation.
- Optional providers: Supabase PostgreSQL, Resend, Upstash QStash, Razorpay Test Mode.
- Hosting: Vercel frontend, Render API.

## Features implemented in source

- Customer registration creates a customer billing profile; login/logout use HTTP-only cookies, CSRF checks protect cookie-authenticated mutations, token-version invalidation revokes sessions on logout/password reset, `/me`, forgot/reset password.
- Admin bootstrap guarded by `ALLOW_ADMIN_BOOTSTRAP`; only admin can create staff.
- Role-aware APIs for admin, staff and customer. Customers can request their own plan subscription; customer records are restricted to their linked profile.
- Products, variants, plans and pricing rules.
- Customer management, quotation templates, quotations and quote-to-subscription conversion.
- Subscription creation, separate confirmation/activation, pause/resume with billing-date adjustment, renewal, closure and expiry handling.
- Billing run endpoint plus QStash signed HTTP endpoint; billing periods and invoices have database uniqueness guards.
- Tax rules and default tax selection; fixed and percentage discount rules with minimum purchase/quantity, date windows and usage caps.
- Invoice snapshots, PDF generation, invoice email, partial payment ledger, PostgreSQL row-locking, manual-payment idempotency keys and Razorpay webhook deduplication.
- Financial KPIs, MRR/ARR normalization, verified collected revenue, outstanding and overdue totals, monthly collection report.
- Audit events for sensitive operations.
- Responsive role-aware workspace UI with live API-backed tables, forms, actions, invoice PDF download and payment recording. List APIs accept bounded `limit`/`offset` pagination; invoices support date/customer/status filters.

## Important integration boundaries

The source code implements provider adapters, but a provider connection is not live until credentials and provider-side settings are supplied:
- Email sending requires verified Resend sender/domain and API key.
- Scheduled billing requires QStash token, both signing keys and a configured schedule.
- Razorpay checkout requires Test Mode API keys and a webhook configured for `payment.captured`.
- Cloud persistence requires a Supabase PostgreSQL connection string.
No provider success is fabricated when credentials are missing. Quotation discount snapshots are not yet frozen through conversion; if discount rules change after quote approval, invoice-time recalculation may diverge from the accepted quotation.

## Local development

### Backend

Python 3.11+ is recommended.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL and SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`; health: `http://localhost:8000/health`.

Create the first admin once:
1. Set `ALLOW_ADMIN_BOOTSTRAP=true`.
2. POST `/api/v1/auth/bootstrap-admin` with `email`, `full_name`, and a strong `password`.
3. Immediately set `ALLOW_ADMIN_BOOTSTRAP=false`.

Optional demo data:
```bash
cd backend
# Set DEMO_ADMIN_PASSWORD, DEMO_STAFF_PASSWORD, DEMO_CUSTOMER_PASSWORD in environment.
python scripts/seed_demo.py
```
The seed creates accounts only when their email is absent and never embeds demo passwords in source.

### Frontend

```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

## Testing

```bash
cd backend
pytest -q
python -m compileall -q app migrations scripts
alembic upgrade head
alembic current
```

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Tests that require a PostgreSQL server or external provider credentials are not equivalent to pure unit tests. Run the documented provider tests against test accounts before production use.

## Deployment

See:
- `render.yaml`
- `vercel.json`
- `backend/.env.example`
- `frontend/.env.example`
- `docs/deployment.md`
- `docs/api-documentation.md`
- `docs/database-schema.md`
- `docs/testing.md`
- `docs/completion-status.md`

### Environment variables

Backend: `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `CORS_ORIGINS`, `ALLOW_ADMIN_BOOTSTRAP`, `FRONTEND_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ACCESS_COOKIE_NAME`, `CSRF_COOKIE_NAME`, `COOKIE_DOMAIN`, `RESEND_API_KEY`, `EMAIL_FROM`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, `QSTASH_TOKEN`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`.

Frontend: `NEXT_PUBLIC_API_URL` and optional `NEXT_PUBLIC_CSRF_COOKIE_NAME`. Never put secrets in `NEXT_PUBLIC_` variables. Never put secrets in `NEXT_PUBLIC_` variables.

## Free-tier caveats

Free plans are suitable for a hackathon demo, not an uptime guarantee:
- Render free web services spin down when idle; free Render Postgres expires after 30 days and free local filesystem changes are not persistent.
- Supabase Free includes 500 MB database, 5 GB egress and 1 GB storage; projects can pause after a week of low database activity.
- Resend Free currently lists 3,000 emails/month and a 100/day limit.
- Upstash QStash Free currently lists 1,000 messages/day.
- Vercel Hobby is for personal/non-commercial use and has usage limits; a commercial SaaS deployment needs an eligible paid plan.
- Razorpay Test Mode does not collect real funds.

Verify live provider pricing, terms and quota dashboards before deployment. See `docs/deployment.md`.

## Current verification note

The backend source and tests were updated in an environment without reliable outbound package-registry DNS/network access. Therefore, package installation, frontend `npm ci`/production build, live PostgreSQL concurrency tests, provider authentication and cloud deployment cannot be truthfully reported as passed here. The source includes test and deployment commands so these checks can be run in the connected development environment.
