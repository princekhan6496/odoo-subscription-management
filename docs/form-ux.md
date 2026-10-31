# Brightloop form and selector UX

## Current implementation

- Customer and plan selectors search live backend records by billing name/email and plan name. The APIs return a bounded 20-record page and support server-side `q` filtering.
- Product selectors search the product catalogue and display the product price. Selecting a product fills its current sales price automatically.
- Product and variant price overrides are disabled for staff in the UI and rejected by the backend; only administrators may override catalogue prices.
- Product variants are loaded from the selected product's variant endpoint. Selecting a variant adds its additional price to the product base price; users can still override the unit price where the business workflow permits it.
- Quotation and quotation-template forms support multiple product lines, quantity changes, optional tax selection and live line-subtotal previews.
- Tax selectors retrieve active tax records; no tax percentage is hardcoded into invoice calculations.
- Discount creation supports fixed/percentage values, minimum spend/quantity, date windows, maximum uses and multiple applicable products. Leaving the product selection empty makes the discount subscription-wide.
- Product, plan, tax and discount creation forms expose active-state toggles. Plan forms expose early-close, pause, renewal and auto-close permissions.
- Staff creation generates a temporary password, with regenerate and copy actions.
- Payment recording starts from a selected invoice row and displays invoice total, amount paid and outstanding balance. It validates the amount against the current displayed outstanding balance; the backend rechecks under an invoice lock and requires an idempotency key.
- Subscription and invoice lists include customer names/emails; subscription rows include plan names and lifecycle permission metadata. Payment rows include invoice/customer references. Raw internal foreign keys are hidden from the primary table view.
- Searchable selectors debounce requests, show loading/error/empty states, support keyboard arrow/enter/escape selection and allow clearing the selected record.

## API search parameters

The following list endpoints accept `q`, `limit` and `offset`:

- `GET /api/v1/customers` (admin/staff)
- `GET /api/v1/products` (admin/staff)
- `GET /api/v1/plans` (admin/staff/customer)
- `GET /api/v1/taxes` (admin/staff)
- `GET /api/v1/discounts` (admin/staff)

## Limitations still present

- The current workspace still uses one consolidated Next.js dashboard page; it has not been decomposed into a full page/component architecture.
- Edit flows are not yet exposed for every entity. Backend PATCH endpoints exist for selected resources, but a full edit/detail experience remains future work.
- Quotation templates and quotation creation now support multiple lines. Subscription creation remains plan-based and does not yet expose an itemized subscription line editor. Quotation creation currently previews line subtotal/tax/total but does not yet apply or snapshot discounts; eligible discounts are applied by the recurring invoice billing engine.
- Search is server-filtered but list total counts, cursor pagination and a full advanced filter bar are not implemented for every resource.
- The UI's product/variant and tax selectors are API-backed, but the frontend production build and browser interaction tests could not be executed because npm dependency installation timed out in this environment.
