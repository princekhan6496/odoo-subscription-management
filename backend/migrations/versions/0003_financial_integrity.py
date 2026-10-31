"""Add financial idempotency and discount allocation fields."""
from alembic import op
import sqlalchemy as sa

revision = "0003_financial_integrity"
down_revision = "0002_business_workflows"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "razorpay_order_id" not in {c["name"] for c in inspector.get_columns("invoices")}:
        with op.batch_alter_table("invoices") as batch:
            batch.add_column(sa.Column("razorpay_order_id", sa.String(80), nullable=True))
    inspector = sa.inspect(bind)
    if "uq_invoices_razorpay_order_id" not in {c.get("name") for c in inspector.get_unique_constraints("invoices")}:
        with op.batch_alter_table("invoices") as batch:
            batch.create_unique_constraint("uq_invoices_razorpay_order_id", ["razorpay_order_id"])
    inspector = sa.inspect(bind)
    if "billing_anchor_day" not in {c["name"] for c in inspector.get_columns("subscriptions")}:
        with op.batch_alter_table("subscriptions") as batch:
            batch.add_column(sa.Column("billing_anchor_day", sa.Integer(), nullable=False, server_default="1"))
        if bind.dialect.name == "postgresql":
            bind.execute(sa.text("UPDATE subscriptions SET billing_anchor_day = EXTRACT(DAY FROM start_date)::integer"))
        elif bind.dialect.name == "sqlite":
            bind.execute(sa.text("UPDATE subscriptions SET billing_anchor_day = CAST(strftime('%d', start_date) AS INTEGER)"))
    inspector = sa.inspect(bind)
    if "token_version" not in {c["name"] for c in inspector.get_columns("users")}:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    inspector = sa.inspect(bind)
    if "discount_amount" not in {c["name"] for c in inspector.get_columns("invoice_items")}:
        with op.batch_alter_table("invoice_items") as batch:
            batch.add_column(sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    inspector = sa.inspect(bind)
    if "idempotency_key" not in {c["name"] for c in inspector.get_columns("payments")}:
        with op.batch_alter_table("payments") as batch:
            batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
    inspector = sa.inspect(bind)
    if "uq_payments_idempotency_key" not in {c.get("name") for c in inspector.get_unique_constraints("payments")}:
        with op.batch_alter_table("payments") as batch:
            batch.create_unique_constraint("uq_payments_idempotency_key", ["idempotency_key"])
    inspector = sa.inspect(bind)
    if "uq_subscriptions_quotation_id" not in {c.get("name") for c in inspector.get_unique_constraints("subscriptions")}:
        with op.batch_alter_table("subscriptions") as batch:
            batch.create_unique_constraint("uq_subscriptions_quotation_id", ["quotation_id"])

def downgrade():
    op.drop_constraint("uq_subscriptions_quotation_id", "subscriptions", type_="unique")
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_column("billing_anchor_day")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_constraint("uq_invoices_razorpay_order_id", type_="unique")
        batch.drop_column("razorpay_order_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
    with op.batch_alter_table("payments") as batch:
        batch.drop_constraint("uq_payments_idempotency_key", type_="unique")
        batch.drop_column("idempotency_key")
    with op.batch_alter_table("invoice_items") as batch:
        batch.drop_column("discount_amount")
