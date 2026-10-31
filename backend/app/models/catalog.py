from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_product_prices_nonnegative"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    product_type: Mapped[str] = mapped_column(String(40), default="service")
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (CheckConstraint("additional_price >= 0", name="ck_variant_price_nonnegative"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    additional_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    product: Mapped[Product] = relationship(back_populates="variants")

class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (CheckConstraint("minimum_quantity >= 1", name="ck_plan_min_quantity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    billing_interval: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    minimum_quantity: Mapped[int] = mapped_column(default=1)
    available_from: Mapped[str | None] = mapped_column(String(10), nullable=True)
    available_until: Mapped[str | None] = mapped_column(String(10), nullable=True)
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_renewal: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
