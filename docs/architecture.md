# Architecture

The application is a modular monolith: one Next.js frontend, one FastAPI backend and one PostgreSQL database.

```mermaid
flowchart LR
  Browser[Next.js web app] -->|HTTPS JSON API + JWT| API[FastAPI]
  API --> ORM[SQLAlchemy services / ORM]
  ORM --> DB[(Supabase PostgreSQL)]
  Scheduler[QStash - later phase] -->|signed HTTP job| API
  API --> Mail[Resend - later phase]
  API --> Pay[Razorpay - optional later phase]
```

Business rules live in backend services, not React components. PostgreSQL constraints and transactions protect important invariants. External integrations are optional adapters and must fail explicitly rather than fabricating success.
