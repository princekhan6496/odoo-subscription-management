# Testing

Backend tests:
```bash
cd backend
pytest -q
python -m compileall -q app migrations scripts
alembic upgrade head
alembic current
```

Frontend:
```bash
cd frontend
npm install
npm run lint
npm run build
```

The backend suite currently covers cookie authentication and CSRF, logout, customer profile patching, role restrictions, quotation conversion, subscription-to-invoice billing, product-specific and multi-product discount/tax allocation, selector search, staff price-override restrictions, human-readable list references, manual-payment idempotency, Razorpay webhook signature/order matching/deduplication, month-end/leap-year date-boundary calculations, server-side selector search, multi-product discount eligibility and one-use-per-invoice accounting, provider-configuration failures, rounding, Argon2 password hashing and JWT subject decoding. PostgreSQL concurrency semantics still require a real PostgreSQL integration run. Razorpay, Resend and QStash live-path tests require provider credentials and must be run in their respective test environments.


## Verification performed in the available workspace

- `python -m compileall -q app migrations scripts tests`: passed.
- `pytest -q`: 23 passed after the latest cookie-auth, session invalidation, quotation, discount and payment-idempotency changes.
- Alembic `upgrade head` and `current`: passed against a temporary SQLite database used strictly as a migration test harness. A real Supabase/PostgreSQL migration still needs to be run after credentials are supplied.
- Demo seed script: executed twice against a temporary test database; it completed idempotently and persisted the demo records.
- Fresh SQLite migration harness: `alembic upgrade head` passed through `0004_discount_product_selection`; `discounts.product_ids` was present and legacy single-product discount backfill ran.

The workspace had no outbound package-registry connectivity. Therefore the pinned `requirements.txt` versions were not installed as a new isolated environment; tests ran against the preinstalled environment versions. `npm install` and the Next.js production build could not run because the registry was unreachable and `node_modules` was absent. `package-lock.json` could not be generated. The TypeScript compiler reported missing framework/type packages; no TypeScript parser/syntax diagnostics were found, but this is not a successful typecheck.
