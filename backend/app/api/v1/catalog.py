from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import Product, ProductVariant, Plan, UserRole
from app.schemas.catalog import ProductCreate, ProductResponse, PlanCreate, PlanResponse
from pydantic import BaseModel, Field
from decimal import Decimal
from app.api.deps import require_roles

router = APIRouter(tags=["catalog"])

class VariantUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    additional_price: Decimal = Field(ge=0)

@router.get("/products", response_model=list[ProductResponse])
def list_products(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    return list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.id.desc()).limit(limit).offset(offset)))

@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = Product(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductCreate, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = db.get(Product, product_id)
    if not item: raise HTTPException(404, "Product not found")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item)
    return item

@router.get("/plans", response_model=list[PlanResponse])
def list_plans(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN, UserRole.STAFF, UserRole.CUSTOMER))):
    return list(db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.id.desc()).limit(limit).offset(offset)))

@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = Plan(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: int, payload: PlanCreate, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = db.get(Plan, plan_id)
    if not item: raise HTTPException(404, "Plan not found")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item)
    return item

@router.delete("/plans/{plan_id}", status_code=204)
def deactivate_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = db.get(Plan, plan_id)
    if not item: raise HTTPException(404, "Plan not found")
    item.is_active = False
    db.commit()
    return None

@router.delete("/products/{product_id}", status_code=204)
def deactivate_product(product_id: int, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = db.get(Product, product_id)
    if not item: raise HTTPException(404, "Product not found")
    item.is_active = False
    db.commit()
    return None

@router.patch("/products/{product_id}/variants/{variant_id}")
def update_variant(product_id: int, variant_id: int, payload: VariantUpdate, db: Session = Depends(get_db), _=Depends(require_roles(UserRole.ADMIN))):
    item = db.get(ProductVariant, variant_id)
    if not item or item.product_id != product_id: raise HTTPException(404, "Variant not found")
    item.name = payload.name
    item.additional_price = payload.additional_price
    db.commit(); db.refresh(item)
    return item
