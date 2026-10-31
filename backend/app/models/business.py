import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, Boolean, ForeignKey, DateTime, Date, Integer, Enum, UniqueConstraint, CheckConstraint, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Status:
    SUBSCRIPTION = ("draft", "quotation", "confirmed", "active", "paused", "closed", "expired")
    INVOICE = ("draft", "confirmed", "partially_paid", "paid", "overdue", "cancelled")

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    company_name: Mapped[str | None] = mapped_column(String(180))
    billing_name: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    billing_address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    validity_days: Mapped[int] = mapped_column(Integer, default=30)
    items: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    valid_until: Mapped[date | None] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    items: Mapped[list["QuotationItem"]] = relationship(cascade="all, delete-orphan")

class QuotationItem(Base):
    __tablename__ = "quotation_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5,2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12,2))

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_due", "status", "next_billing_date"), UniqueConstraint("quotation_id", name="uq_subscriptions_quotation_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    start_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    next_billing_date: Mapped[date | None] = mapped_column(Date, index=True)
    billing_anchor_day: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=15)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    items: Mapped[list["SubscriptionItem"]] = relationship(cascade="all, delete-orphan")

class SubscriptionItem(Base):
    __tablename__ = "subscription_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5,2), default=0)

class Tax(Base):
    __tablename__ = "taxes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    rate: Mapped[Decimal] = mapped_column(Numeric(5,2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Discount(Base):
    __tablename__ = "discounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # fixed / percentage
    value: Mapped[Decimal] = mapped_column(Numeric(12,2))
    min_purchase: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[date | None] = mapped_column(Date)
    ends_at: Mapped[date | None] = mapped_column(Date)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("subscription_id", "billing_period_start", name="uq_invoice_subscription_cycle"), UniqueConstraint("razorpay_order_id", name="uq_invoices_razorpay_order_id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    billing_period_start: Mapped[date | None] = mapped_column(Date)
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    items: Mapped[list["InvoiceItem"]] = relationship(cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5,2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12,2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0, server_default="0")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    method: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reference: Mapped[str | None] = mapped_column(String(160), unique=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    note: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

class BillingCycle(Base):
    __tablename__ = "billing_cycles"
    __table_args__ = (UniqueConstraint("subscription_id", "period_start", name="uq_billing_cycle"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    state: Mapped[str] = mapped_column(String(20), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
