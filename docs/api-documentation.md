# API overview

Base path: `/api/v1`. Swagger UI: `/docs`.

- Auth: `POST /auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/bootstrap-admin`. Browser auth uses HTTP-only cookies plus `X-CSRF-Token` for unsafe methods; bearer tokens remain accepted for non-browser API clients.
- Customers/staff: `/customers`, `/customers/me`, `/staff`, `/staff/{id}/deactivate`.
- Catalogue: `/products`, `/products/{id}`, `/products/{id}/variants`, `/plans` (including patch/deactivate), variant update/delete.
- Quotations: `/quotation-templates`, `/quotations`, `/quotations/{id}/convert`.
- Subscriptions: `/subscriptions`, `POST /subscriptions/request` (customer self-service draft request), `/subscriptions/{id}`, `/subscriptions/{id}/action/{quotation|confirm|activate|pause|resume|renew|close|expire}`.
- Taxes/discounts: `/taxes`, `/discounts` (admin-managed create/update/deactivate).
- Billing: `POST /billing/run` (admin manual run), `POST /billing/qstash` (signed QStash job).
- Invoices: `/invoices`, `/invoices/{id}/confirm`, `/invoices/{id}/cancel`, `/invoices/{id}/pdf`, `/invoices/{id}/send`, `/invoices/{id}/payments`, `/invoices/{id}/razorpay-order`.
- Payments/webhooks: `/payments`, `/webhooks/razorpay`.
- Analytics: `/dashboard/summary`, `/reports/monthly-revenue`.
- Audit: `/audit-logs` (admin).

List endpoints accept bounded `limit` and `offset` query parameters; invoices also accept `status_filter`, `customer_id` (staff only), `date_from` and `date_to`. Manual payment recording requires an `Idempotency-Key` header. Role authorization is enforced on the backend. Customer list endpoints are scoped to the signed-in customer's linked profile. Never trust a client-supplied customer ID without checking ownership.

## Financial metric definitions

- **MRR** is the sum of active subscription plan price × subscription quantity, normalized to a monthly amount (daily × 30; weekly × 52/12; monthly × 1; yearly ÷ 12). It is a gross contracted run-rate and excludes taxes, one-off invoice items and applied discounts.
- **ARR** is MRR × 12.
- **Collected revenue** is the sum of verified payment ledger entries in the selected period; it is not the sum of invoices issued.
- **Outstanding** is the sum of non-cancelled invoice total minus successful/verified payments recorded against each invoice.
