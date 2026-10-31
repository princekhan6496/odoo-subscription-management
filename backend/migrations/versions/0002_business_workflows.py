"""Add customer, quotation, subscription, billing, invoice and payment workflows."""
from alembic import op
from app.db import Base
from app import models

revision = "0002_business_workflows"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    # SQLAlchemy metadata is the canonical declaration for this migration.
    # checkfirst makes this safe for an already-initialized database.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)

def downgrade():
    # Keep destructive rollback explicit; business data should not be dropped accidentally.
    raise RuntimeError("This migration is intentionally irreversible; take a database backup before schema rollback.")
