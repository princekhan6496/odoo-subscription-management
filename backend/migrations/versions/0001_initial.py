"""Initial users and catalog schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    role = sa.Enum("ADMIN", "STAFF", "CUSTOMER", name="user_role")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("product_type", sa.String(40), nullable=False),
        sa.Column("sales_price", sa.Numeric(12,2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12,2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_product_prices_nonnegative"),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("additional_price", sa.Numeric(12,2), nullable=False),
        sa.CheckConstraint("additional_price >= 0", name="ck_variant_price_nonnegative"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("price", sa.Numeric(12,2), nullable=False),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("available_from", sa.String(10)),
        sa.Column("available_until", sa.String(10)),
        sa.Column("auto_close", sa.Boolean(), nullable=False),
        sa.Column("allow_early_close", sa.Boolean(), nullable=False),
        sa.Column("allow_pause", sa.Boolean(), nullable=False),
        sa.Column("allow_renewal", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("minimum_quantity >= 1", name="ck_plan_min_quantity"),
    )
    op.create_index("ix_plans_name", "plans", ["name"])

def downgrade():
    op.drop_index("ix_plans_name", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
