# Database schema

Core entities:
- `users`: login identity, role, active state, token version and Argon2 hash.
- `customers`: billing identity linked optionally to a customer user.
- `products`, `product_variants`, `plans`: catalogue and price configuration.
- `quotation_templates`, `quotations`, `quotation_items`: reusable offers and accepted commercial terms.
- `subscriptions`, `subscription_items`: recurring customer agreements, frozen line pricing and a preserved monthly billing anchor day.
- `taxes`, `discounts`: admin-managed pricing rules and usage counts.
- `invoices`, `invoice_items`: immutable billing snapshots, tax, discount, Razorpay order reference, paid and outstanding amounts.
- `payments`: payment ledger, references, idempotency keys and verification state.
- `billing_cycles`: unique subscription-period idempotency key.
- `password_resets`: hashed one-time reset tokens and expiry.
- `audit_logs`: actor, action, entity and JSON details.

Money uses fixed precision `NUMERIC(12,2)`, not binary floating-point. Invoices preserve their own line snapshots, including per-line discount amounts, so later catalogue price changes do not rewrite issued invoices.

Discount product targeting now supports multiple catalogue products through `discounts.product_ids` (JSON array). The legacy `product_id` field is retained for compatibility; migration `0004_discount_product_selection` backfills existing single-product rules into the new collection. A product-targeted discount is counted once per invoice even when it applies to multiple invoice lines.
