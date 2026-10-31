from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Literal

class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    product_type: Literal["service", "goods", "software"] = "service"
    sales_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None
    is_active: bool = True

class ProductResponse(ProductCreate):
    id: int
    is_active: bool
    model_config = {"from_attributes": True}

class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    billing_interval: Literal["daily", "weekly", "monthly", "yearly"]
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    minimum_quantity: int = Field(default=1, ge=1)
    available_from: str | None = None
    available_until: str | None = None
    auto_close: bool = False
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renewal: bool = True
    is_active: bool = True

class PlanResponse(PlanCreate):
    id: int
    is_active: bool
    model_config = {"from_attributes": True}
