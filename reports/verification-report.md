# Brightloop verification report

Date: 2026-10-31

## Passed

| Check | Result | Scope |
|---|---|---|
| Python compileall | PASS | `app`, `migrations`, `scripts`, `tests` |
| Backend pytest | PASS — 23 tests | Cookie auth/CSRF, session invalidation, role checks, customer isolation, quotation conversion, subscription lifecycle, invoice/payment flow, discount/tax calculations, multi-product discounts and invoice-level usage limits, selector search, webhook verification/deduplication, date boundaries, provider configuration errors |
| Alembic upgrade head | PASS | Temporary SQLite migration harness through `0004_discount_product_selection` |
| Legacy discount backfill | PASS | A legacy `product_id` was migrated into the new `product_ids` JSON array |
| Frontend TSX syntax parse | PASS | TypeScript compiler parser reported zero syntax diagnostics for `page.tsx`, `async-combobox.tsx` and `async-multi-select.tsx` |
| ZIP integrity | PASS | `unzip -t` reported no archive errors |

## Blocked / not run successfully

| Check | Result | Reason |
|---|---|---|
| Pinned Python clean install | BLOCKED | Package registry DNS/network unavailable |
| npm install / lockfile | BLOCKED | npm registry request timed out; no `package-lock.json` or `node_modules` could be produced |
| Next.js production build | BLOCKED | `next` is not installed because npm install could not complete |
| ESLint / full TypeScript typecheck | BLOCKED | React, Next.js and framework/type packages are not installed. Parser validation is not a typecheck. |
| PostgreSQL migration and concurrency | NOT RUN | No Supabase/PostgreSQL credentials or reachable database; SQLite does not verify PostgreSQL row-lock semantics |
| Resend/QStash/Razorpay live sandbox | NOT RUN | Provider credentials and account configuration unavailable |
| Cloud deployments | NOT RUN | No connected Vercel/Render/Supabase projects or credentials |
| Physical-device mobile/performance test | NOT RUN | No iOS/Android device test session or load-test environment |

## Environment used for passing backend tests

The available preinstalled runtime was used rather than a clean install of the newly pinned dependency set. The environment's installed packages may differ from the exact pins in `backend/requirements.txt`; those exact pins still need a clean installation and verification in an internet-connected environment.
