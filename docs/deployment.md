# Cloud deployment

## Services

- Vercel: Next.js frontend.
- Render: FastAPI web service.
- Supabase: managed PostgreSQL.
- Resend: transactional email API.
- Upstash QStash: signed scheduled HTTP delivery.
- Razorpay: optional online checkout in Test Mode.

The core product works with PostgreSQL and manual payments even when the optional provider credentials are absent. Provider integrations return explicit configuration errors rather than fake success.

## Supabase

Create a project, copy its PostgreSQL connection string, and set `DATABASE_URL` on Render. Prefer the direct connection for Render when supported by the chosen network mode; use the Supavisor pooler connection for constrained connection environments. Require TLS (`sslmode=require`). Never expose the database password or service-role key in a `NEXT_PUBLIC_` variable.

Free projects can pause after a week of low activity. Keep real activity or restore the project when paused. Do not promise production uptime from the free tier.

## Render

Create a web service from this repository. `render.yaml` configures the Python service. Set secrets from `backend/.env.example` in the Render dashboard. Configure the frontend and API on custom hostnames under the same registrable domain (for example `app.example.com` and `api.example.com`) for reliable cookie delivery; set `COOKIE_DOMAIN=.example.com`, `ENVIRONMENT=production`, and the exact `CORS_ORIGINS` value. The start command runs Alembic migrations before Uvicorn. Render free web services sleep when idle and have no persistent local filesystem; this app stores business records in Supabase, not local disk.

## Vercel

Import the repository and set the project root to `frontend`. Set `NEXT_PUBLIC_API_URL` to the deployed Render API origin. `vercel.json` selects Next.js and `npm ci`. The Hobby plan is aimed at personal/non-commercial use; check current terms for hackathon and commercial eligibility.

## Resend

Verify a sending domain and create an API key. Set `RESEND_API_KEY`, `EMAIL_FROM`, and `FRONTEND_URL`. Without these, password-reset requests return a generic response; in development the reset token is returned for local testing. Invoice email returns HTTP 503 until configured.

## Upstash QStash

Create a QStash token and copy both current and next signing keys into Render. Schedule a POST to `https://YOUR_RENDER_HOST/api/v1/billing/qstash` with the QStash schedule API, for example:
```bash
curl -X POST "https://qstash.upstash.io/v2/schedules/https://YOUR_RENDER_HOST/api/v1/billing/qstash" \
  -H "Authorization: Bearer $QSTASH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cron":"0 2 * * *","body":"{}"}'
```
QStash free tier lists 1,000 messages/day. For larger volumes, use paid usage or reduce schedule frequency. Billing is idempotent at the subscription/billing-period level.

## Razorpay

Create Test Mode API keys. Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and a webhook secret. Configure the webhook URL as `https://YOUR_RENDER_HOST/api/v1/webhooks/razorpay` and subscribe to `payment.captured`. The backend creates orders; the invoice balance changes only after a valid signed captured-payment webhook. Test credentials do not collect real money.

## Initial admin and demo seed

1. Temporarily set `ALLOW_ADMIN_BOOTSTRAP=true`.
2. Deploy or run backend, then POST `/api/v1/auth/bootstrap-admin` with an admin email, strong password and full name.
3. Set `ALLOW_ADMIN_BOOTSTRAP=false` immediately.
4. Optionally run `python scripts/seed_demo.py` from `backend/` with `DEMO_ADMIN_PASSWORD`, `DEMO_STAFF_PASSWORD`, and `DEMO_CUSTOMER_PASSWORD` set. The script never ships hard-coded demo passwords.
5. Do not run the demo seed in production unless you intentionally want demo records.

## Migrations

```bash
cd backend
alembic upgrade head
alembic current
```

Back up Supabase before applying schema changes. Migration 0002 creates business tables from SQLAlchemy metadata and is intentionally non-reversible. Migration 0003 adds invoice discount allocation and payment idempotency fields and a unique quotation conversion constraint.


## Verified free-tier constraints (checked 2026-10-31)

| Provider | Relevant free allowance / restriction | Engineering implication |
|---|---|---|
| Vercel Hobby | Free, with usage quotas; personal/non-commercial use only | Confirm hackathon usage is eligible; a commercial Brightloop deployment needs the appropriate plan |
| Render Free | 750 free instance-hours/workspace/month; free web services spin down; free Postgres is 1 GB and expires after 30 days; no persistent filesystem | Use Render only for the demo API, never local disk or Render free Postgres as durable production storage |
| Supabase Free | 500 MB database, 5 GB egress, 1 GB file storage; up to two active free projects; pauses after roughly seven days of low activity | Keep data compact, generate invoice PDFs on demand, and expect occasional project resume operations |
| Resend Free | 3,000 emails/month, capped at 100/day | Email volume is capped; handle provider rate-limit failures |
| Upstash QStash Free | 1,000 messages/day | A single scheduled billing message is cheap; large fan-out jobs must be batched or paid |
| Razorpay Test Mode | Simulated test transactions; no real funds are collected | Demonstrates checkout only; live mode requires separate keys and account activation |

These are provider plan limits, not guarantees of availability. Check the live dashboard before a public demo; providers can change quotas and eligibility.


## Browser authentication cookies

The frontend uses `credentials: include`; the API sets an HTTP-only access cookie and a separate CSRF cookie. Production cookies require HTTPS and `SameSite=None` because the frontend and API use separate subdomains. Keep `CORS_ORIGINS` restricted to the exact frontend origin. Set `COOKIE_DOMAIN` to the shared parent domain only when the frontend/API hostnames are under that domain. Do not use the default Vercel/Render hostnames for production browser sessions if third-party-cookie blocking prevents the API cookie from being sent.
