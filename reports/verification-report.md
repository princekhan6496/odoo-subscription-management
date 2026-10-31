# Brightloop verification report

Date: 2026-10-31

## Passed

| Check | Result | Scope |
|---|---|---|
| Python compileall | PASS | `app`, `migrations`, `scripts`, `tests` |
| Backend pytest | PASS — 9 tests | Auth/security, role checks, subscription activation, recurring invoice generation, partial payment and duplicate payment reference |
| Alembic upgrade/current | PASS | Temporary SQLite migration harness only; current revision `0002_business_workflows` |
| Demo seed repeatability | PASS | Temporary SQLite harness; two consecutive runs completed without duplicate sample records |
| ZIP integrity | PASS | `unzip -t` reported no archive errors |

## Blocked / not run successfully

| Check | Result | Reason |
|---|---|---|
| Pinned Python clean install | BLOCKED | Package registry DNS/network unavailable |
| npm install / lockfile | BLOCKED | npm registry request timed out; offline cache did not contain required packages |
| Next.js production build | BLOCKED | `next` is not installed because npm install could not complete |
| Full TypeScript typecheck | BLOCKED | React, Next.js and type packages are not installed; no parser/syntax diagnostics were emitted |
| PostgreSQL migration | NOT RUN | No Supabase/PostgreSQL credentials or reachable database |
| Resend/QStash/Razorpay live sandbox | NOT RUN | Provider credentials and account configuration unavailable |
| Cloud deployments | NOT RUN | No connected Vercel/Render/Supabase projects or credentials |
| Physical-device mobile/performance test | NOT RUN | No iOS/Android device test session |

## Environment used for passing backend tests

The available preinstalled runtime was used rather than a clean install of the newly pinned dependency set. The environment had FastAPI 0.128.2, SQLAlchemy 2.0.50, Pydantic 2.13.5, Alembic 1.18.4, Argon2 25.1.0, HTTPX 0.28.1, ReportLab 4.4.9 and pytest 9.0.2.

The dependency pins in `backend/requirements.txt` target the newer versions documented in the README; those exact pins still need a clean installation and verification in an internet-connected environment.
