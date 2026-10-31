# Implementation roadmap

1. Foundation: project structure, configuration, PostgreSQL, migrations, auth and catalog APIs.
2. Customer/staff administration, customer isolation, variants and full plan configuration.
3. Quotations, quotation templates and subscription lifecycle with transactional state transitions.
4. Tax and discount rules with concurrency-safe usage accounting.
5. Invoice generation, invoice PDF and billing-cycle idempotency.
6. Payment ledger, partial payments and optional verified Razorpay webhooks.
7. QStash scheduled billing and retry-safe processing.
8. Database-backed reporting, filters and performance measurement.
9. UI workflow completion, accessibility, tests and deployment verification.
