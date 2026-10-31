# Brightloop completion and verification status

This document separates code that has been implemented and locally checked from work that still requires an external service, a full frontend dependency installation, or further product implementation.

## Implemented in the current source tree

- Role-based admin, staff and customer APIs; customer data scoping; Argon2 password hashing.
- Browser authentication through HTTP-only access cookies, CSRF cookie/header validation, logout and token-version invalidation on logout/password reset. Bearer authentication remains available for API clients.
- Customer registration/profile, customer self-service subscription requests, staff management and catalogue/plan endpoints.
- Quotation creation/conversion. Conversion creates a confirmed subscription; activation remains a separate action. Quotation row locking and a unique subscription quotation reference prevent duplicate conversions.
- Subscription confirmation, activation, pause/resume, renewal, closure and expiry transitions. Paused time shifts the next billing and expiry dates; a stored billing anchor preserves month-end and leap-day recurrence.
- Invoice generation with product-specific discount deduction from taxable line bases, subscription-wide discount allocation, tax calculation, partial/full payments and outstanding balance tracking.
- PostgreSQL row locks on invoice payment and due-subscription processing paths; unique invoice-per-subscription-period constraints; manual-payment idempotency keys; Razorpay webhook signature verification, stored-order matching and payment-reference deduplication; QStash delivery verification and schedule helper.
- Password-reset token expiry, single-use semantics, replacement-token invalidation and session token-version revocation. Login/password-reset rate limiting and optional email verification are not yet implemented.
- Paginated list APIs with bounded `limit`/`offset`; invoice status/date/customer filters; MRR calculated with one SQL aggregation rather than per-subscription plan lookups.
- PDF invoice generation, Resend email calls, QStash signature receiver and scheduling helper, Razorpay order creation and webhook endpoint.
- Render/Vercel configuration, environment templates, seed script, API/database/deployment documentation.
- UI motion reduced to restrained press feedback, pointer-gated hover behavior and reduced-motion support.

## Checks that passed in this workspace

- `python -m compileall -q app migrations scripts tests` — passed.
- `pytest -q` — **20 passed**.
- `alembic upgrade head` and `alembic current` — passed against a temporary SQLite migration harness; head is `0003_financial_integrity`.
- Demo seed script was run twice against a temporary SQLite test database and completed idempotently in the earlier verification pass.
- ZIP archive integrity is checked again before final delivery.

## Not verified or still incomplete

- The npm registry timed out. No `package-lock.json` could be generated; `npm ci`, ESLint, TypeScript and the Next.js production build are not verified. `node_modules` is absent.
- Ruff is not installed in this runtime, so lint could not be run.
- PostgreSQL-specific row-lock and concurrent-worker behavior has not been tested against a live PostgreSQL server. SQLite migration tests do not validate `SELECT FOR UPDATE` semantics.
- Resend, QStash, Razorpay, Supabase, Render and Vercel have not been connected or deployed with live credentials. No provider success is claimed.
- The default Vercel and Render hostnames may be treated as cross-site for cookies and can be blocked by browser third-party-cookie restrictions. Use frontend/API custom hostnames under the same registrable domain and configure `COOKIE_DOMAIN` for production.
- Quotation discounts are not yet persisted as immutable discount snapshots through conversion; invoice billing recalculates the active discount rules, so a rule changed after quote acceptance can make the invoice differ from the quotation. Advanced filters and total-count metadata are not implemented on every list; the current frontend does not yet expose all server pagination controls.
- The frontend remains a consolidated dashboard page rather than a complete componentized suite. Full edit workflows for every entity, customer invitation/verification, subscription purchase/checkout beyond a draft request, automated notification dispatch for all lifecycle events, payment reversals/refunds, and full browser/mobile E2E coverage remain incomplete.
- Performance under thousands of records and the original under-two-second page target has not been benchmarked.

## Emil Kowalski skills

The requested `npx skills@latest add emilkowalski/skills` installation timed out in earlier attempts; a local installation could not be verified. Relevant published skill instructions were reviewed and selected guidance was applied manually. In particular, the animation review follows the repository's principles: no `transition: all`, restrained short press feedback, no layout-property animation, pointer-gated hover, and reduced-motion handling.

## Required external setup

- Supabase PostgreSQL connection string and a fresh-database migration run.
- Render backend service and environment variables.
- Vercel frontend project with `NEXT_PUBLIC_API_URL`.
- Custom frontend/API hostnames under the same site for reliable production cookie behavior.
- Resend verified sender/domain and API key.
- Upstash QStash token, current/next signing keys and a configured schedule.
- Razorpay Test Mode key ID, key secret and webhook secret, plus the `payment.captured` webhook.
- Initial admin password and optional demo passwords supplied through environment variables.
