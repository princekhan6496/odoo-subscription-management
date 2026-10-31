from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
import hashlib, hmac, secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import *
from app.api.deps import current_user, require_roles
from app.core.security import hash_password, verify_password
from app.core.config import settings

router = APIRouter(tags=["business operations"])
ADMIN_STAFF = (UserRole.ADMIN, UserRole.STAFF)

def audit(db, actor, action, entity, entity_id, details=None):
    db.add(AuditLog(actor_user_id=actor.id if actor else None, action=action, entity_type=entity, entity_id=str(entity_id), details=details or {}))

def customer_scope(db: Session, user: User):
    if user.role == UserRole.CUSTOMER:
        customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
        if not customer: raise HTTPException(404, "Customer profile not found")
        return customer.id
    return None

def ensure_customer_access(db, user, customer_id):
    scope = customer_scope(db, user)
    if scope is not None and scope != customer_id:
        raise HTTPException(403, "You cannot access another customer's records")

def money(v):
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def next_date(start: date, interval: str, anchor_day: int | None = None):
    if interval == "daily": return start + timedelta(days=1)
    if interval == "weekly": return start + timedelta(days=7)
    anchor_day = anchor_day or start.day
    import calendar
    if interval == "yearly":
        last_day=calendar.monthrange(start.year+1,start.month)[1]
        return start.replace(year=start.year+1,day=min(anchor_day,last_day))
    month = start.month + 1
    year = start.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return start.replace(year=year, month=month, day=min(anchor_day, calendar.monthrange(year, month)[1]))

class CustomerIn(BaseModel):
    billing_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    company_name: str | None = None
    phone: str | None = None
    billing_address: str | None = None
    tax_id: str | None = None

class CustomerPatch(BaseModel):
    billing_name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    company_name: str | None = None
    phone: str | None = None
    billing_address: str | None = None
    tax_id: str | None = None

class StaffIn(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=9, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str):
        import re
        if not re.search(r"[A-Z]",value) or not re.search(r"[a-z]",value) or not re.search(r"[^A-Za-z0-9]",value):
            raise ValueError("Password must contain uppercase, lowercase and special characters")
        return value

class VariantIn(BaseModel):
    name: str
    additional_price: Decimal = Field(ge=0)

class QuoteItemIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100)

class QuoteIn(BaseModel):
    customer_id: int
    plan_id: int | None = None
    template_id: int | None = None
    validity_days: int = Field(default=30, ge=1, le=365)
    items: list[QuoteItemIn] = []

class SubscriptionIn(BaseModel):
    customer_id: int
    plan_id: int
    start_date: date
    expiry_date: date | None = None
    quantity: int = Field(default=1, ge=1)
    payment_terms_days: int = Field(default=15, ge=0, le=120)
    items: list[QuoteItemIn] = []

class SubscriptionRequestIn(BaseModel):
    plan_id: int
    quantity: int = Field(default=1, ge=1)
    start_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())

class TaxIn(BaseModel):
    name: str
    rate: Decimal = Field(ge=0, le=100)

class DiscountIn(BaseModel):
    name: str
    kind: str
    value: Decimal = Field(gt=0)
    min_purchase: Decimal = Field(default=0, ge=0)
    min_quantity: int = Field(default=1, ge=1)
    starts_at: date | None = None
    ends_at: date | None = None
    max_uses: int | None = Field(default=None, ge=1)
    product_id: int | None = None

class PaymentIn(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    reference: str | None = None
    note: str | None = None

class ResetRequest(BaseModel):
    email: EmailStr

class ResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=9, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str):
        import re
        if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain uppercase, lowercase and special characters")
        return value


@router.get("/customers/me")
def customer_profile(db:Session=Depends(get_db),user:User=Depends(current_user)):
    cid=customer_scope(db,user)
    if cid is None: raise HTTPException(403,"Customer portal only")
    obj=db.get(Customer,cid)
    return obj

@router.patch("/customers/me")
def update_customer_profile(payload:CustomerPatch,db:Session=Depends(get_db),user:User=Depends(current_user)):
    cid=customer_scope(db,user)
    if cid is None: raise HTTPException(403,"Customer portal only")
    obj=db.get(Customer,cid)
    updates=payload.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"]=updates["email"].lower()
        if db.scalar(select(Customer).where(Customer.email==updates["email"],Customer.id!=obj.id)):
            raise HTTPException(409,"A customer with this email already exists")
    for key,value in updates.items(): setattr(obj,key,value)
    audit(db,user,"customer.profile_updated","customer",obj.id)
    db.commit(); db.refresh(obj); return obj

@router.get("/customers")
def customers(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db: Session=Depends(get_db), user: User=Depends(require_roles(*ADMIN_STAFF))):
    return db.scalars(select(Customer).order_by(Customer.id.desc()).limit(limit).offset(offset)).all()

@router.post("/customers", status_code=201)
def create_customer(payload: CustomerIn, db: Session=Depends(get_db), user: User=Depends(require_roles(*ADMIN_STAFF))):
    if db.scalar(select(Customer).where(Customer.email==payload.email.lower())):
        raise HTTPException(409,"A customer with this email already exists")
    values=payload.model_dump()
    values["email"]=values["email"].lower()
    obj=Customer(**values)
    db.add(obj); db.flush(); audit(db,user,"customer.created","customer",obj.id); db.commit(); db.refresh(obj)
    return obj

@router.patch("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CustomerPatch, db: Session=Depends(get_db), user: User=Depends(require_roles(*ADMIN_STAFF))):
    obj=db.get(Customer,customer_id)
    if not obj: raise HTTPException(404,"Customer not found")
    updates=payload.model_dump(exclude_unset=True)
    if "email" in updates and db.scalar(select(Customer).where(Customer.email==updates["email"].lower(),Customer.id!=obj.id)):
        raise HTTPException(409,"A customer with this email already exists")
    if "email" in updates: updates["email"]=updates["email"].lower()
    for k,v in updates.items(): setattr(obj,k,v)
    audit(db,user,"customer.updated","customer",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/staff")
def list_staff(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db: Session=Depends(get_db), user: User=Depends(require_roles(UserRole.ADMIN))):
    users=db.scalars(select(User).where(User.role==UserRole.STAFF).order_by(User.id.desc()).limit(limit).offset(offset)).all()
    return [{"id":u.id,"email":u.email,"full_name":u.full_name,"role":u.role,"is_active":u.is_active} for u in users]

@router.post("/staff",status_code=201)
def create_staff(payload: StaffIn, db: Session=Depends(get_db), user: User=Depends(require_roles(UserRole.ADMIN))):
    email=payload.email.lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already exists")
    obj=User(email=email,full_name=payload.full_name,password_hash=hash_password(payload.password),role=UserRole.STAFF)
    db.add(obj); audit(db,user,"staff.created","user",email); db.commit(); db.refresh(obj); return {"id":obj.id,"email":obj.email,"full_name":obj.full_name,"role":obj.role}


@router.post("/staff/{staff_id}/deactivate")
def deactivate_staff(staff_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    staff=db.get(User,staff_id)
    if not staff or staff.role!=UserRole.STAFF: raise HTTPException(404,"Staff member not found")
    staff.is_active=False
    audit(db,user,"staff.deactivated","user",staff.id)
    db.commit()
    return {"id":staff.id,"is_active":False}

@router.post("/products/{product_id}/variants",status_code=201)
def add_variant(product_id:int,payload:VariantIn,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Product not found")
    v=ProductVariant(product_id=product_id,**payload.model_dump()); db.add(v); audit(db,user,"variant.created","product_variant",product_id); db.commit(); db.refresh(v)
    return {"id":v.id,"product_id":v.product_id,"name":v.name,"additional_price":v.additional_price,"final_price":money(product.sales_price+v.additional_price)}


@router.delete("/products/{product_id}/variants/{variant_id}",status_code=204)
def delete_variant(product_id:int,variant_id:int,db:Session=Depends(get_db),_ = Depends(require_roles(UserRole.ADMIN))):
    item=db.get(ProductVariant,variant_id)
    if not item or item.product_id!=product_id: raise HTTPException(404,"Variant not found")
    db.delete(item); db.commit()
    return None

@router.get("/products/{product_id}/variants")
def variants(product_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    return db.scalars(select(ProductVariant).where(ProductVariant.product_id==product_id)).all()

@router.post("/quotation-templates",status_code=201)
def create_template(payload:dict,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    obj=QuotationTemplate(name=payload["name"],validity_days=int(payload.get("validity_days",30)),items=payload.get("items",[]))
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/quotation-templates")
def templates(db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    return db.scalars(select(QuotationTemplate).where(QuotationTemplate.is_active.is_(True))).all()


@router.patch("/quotation-templates/{template_id}")
def update_template(template_id:int,payload:dict,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    obj=db.get(QuotationTemplate,template_id)
    if not obj: raise HTTPException(404,"Template not found")
    if "name" in payload: obj.name=str(payload["name"])[:160]
    if "validity_days" in payload: obj.validity_days=max(1,min(365,int(payload["validity_days"])))
    if "items" in payload: obj.items=payload["items"]
    db.commit(); db.refresh(obj); return obj

@router.delete("/quotation-templates/{template_id}",status_code=204)
def deactivate_template(template_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    obj=db.get(QuotationTemplate,template_id)
    if not obj: raise HTTPException(404,"Template not found")
    obj.is_active=False; db.commit(); return None

@router.post("/quotations/{quote_id}/cancel")
def cancel_quotation(quote_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    obj=db.get(Quotation,quote_id)
    if not obj: raise HTTPException(404,"Quotation not found")
    if obj.status not in ("draft","quotation"): raise HTTPException(409,"Quotation can no longer be cancelled")
    obj.status="cancelled"; audit(db,user,"quotation.cancelled","quotation",obj.number); db.commit()
    return {"id":obj.id,"status":obj.status}

@router.post("/quotations",status_code=201)
def create_quote(payload:QuoteIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    customer=db.get(Customer,payload.customer_id)
    if not customer: raise HTTPException(404,"Customer not found")
    q=Quotation(number=f"QUO-{uuid4().hex[:10].upper()}",customer_id=customer.id,plan_id=payload.plan_id,status="quotation",valid_until=datetime.now(timezone.utc).date()+timedelta(days=payload.validity_days))
    subtotal=Decimal("0"); tax=Decimal("0")
    db.add(q); db.flush()
    quote_lines=payload.items
    if not quote_lines and payload.template_id:
        template=db.get(QuotationTemplate,payload.template_id)
        if not template or not template.is_active: raise HTTPException(404,"Quotation template not found")
        quote_lines=[QuoteItemIn.model_validate(item) for item in template.items]
        q.valid_until=datetime.now(timezone.utc).date()+timedelta(days=template.validity_days)
    for line in quote_lines:
        product=db.get(Product,line.product_id)
        if not product or not product.is_active: raise HTTPException(400,f"Invalid product {line.product_id}")
        unit=line.unit_price if line.unit_price is not None else product.sales_price
        if line.variant_id:
            variant=db.get(ProductVariant,line.variant_id)
            if not variant or variant.product_id != product.id: raise HTTPException(400,"Variant does not belong to product")
            if line.unit_price is None: unit += variant.additional_price
        tax_rate=line.tax_rate
        if tax_rate is None:
            default_tax=db.scalar(select(Tax).where(Tax.is_active.is_(True)).order_by(Tax.id).limit(1))
            tax_rate=default_tax.rate if default_tax else Decimal("0")
        base=money(unit*line.quantity); tax_line=money(base*tax_rate/100)
        subtotal+=base; tax+=tax_line
        q.items.append(QuotationItem(product_id=product.id,variant_id=line.variant_id,description=product.name,quantity=line.quantity,unit_price=unit,tax_rate=tax_rate,line_total=base+tax_line))
    q.subtotal=money(subtotal); q.tax_total=money(tax); q.total=money(subtotal+tax)
    audit(db,user,"quotation.created","quotation",q.number); db.commit(); db.refresh(q)
    return {"id":q.id,"number":q.number,"status":q.status,"customer_id":q.customer_id,"valid_until":q.valid_until,"subtotal":q.subtotal,"tax_total":q.tax_total,"total":q.total,"items":[{"description":i.description,"quantity":i.quantity,"unit_price":i.unit_price,"line_total":i.line_total} for i in q.items]}

@router.get("/quotations")
def list_quotes(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),status_filter:str|None=None,customer_id:int|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    stmt=select(Quotation).order_by(Quotation.id.desc())
    if user.role==UserRole.CUSTOMER:
        cid=customer_scope(db,user); stmt=stmt.where(Quotation.customer_id==cid)
    elif customer_id is not None:
        stmt=stmt.where(Quotation.customer_id==customer_id)
    if status_filter: stmt=stmt.where(Quotation.status==status_filter)
    return db.scalars(stmt.limit(limit).offset(offset)).all()

@router.post("/quotations/{quote_id}/convert",status_code=201)
def convert_quote(quote_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    q=db.scalar(select(Quotation).where(Quotation.id==quote_id).with_for_update())
    if not q: raise HTTPException(404,"Quotation not found")
    if q.status not in ("quotation","draft"): raise HTTPException(409,"Quotation cannot be converted")
    if q.valid_until and q.valid_until < datetime.now(timezone.utc).date(): raise HTTPException(409,"Quotation expired")
    plan=db.get(Plan,q.plan_id) if q.plan_id else None
    if not plan or not plan.is_active: raise HTTPException(400,"Quotation must reference an active plan")
    today=datetime.now(timezone.utc).date()
    if plan.available_from and today.isoformat()<plan.available_from: raise HTTPException(409,"Plan is not available yet")
    if plan.available_until and today.isoformat()>plan.available_until: raise HTTPException(409,"Plan is no longer available")
    if not q.items: raise HTTPException(409,"Quotation has no valid line items")
    for line in q.items:
        product=db.get(Product,line.product_id)
        if not product or not product.is_active: raise HTTPException(409,"A quoted product is no longer available")
    sub=Subscription(number=f"SUB-{uuid4().hex[:10].upper()}",customer_id=q.customer_id,plan_id=plan.id,quotation_id=q.id,status="confirmed",start_date=today,next_billing_date=today,quantity=plan.minimum_quantity,billing_anchor_day=today.day)
    db.add(sub); db.flush()
    for i in q.items:
        sub.items.append(SubscriptionItem(product_id=i.product_id,variant_id=i.variant_id,description=i.description,quantity=i.quantity,unit_price=i.unit_price,tax_rate=i.tax_rate))
    q.status="confirmed"; audit(db,user,"quotation.converted","subscription",sub.number); db.commit(); db.refresh(sub)
    return sub

@router.post("/subscriptions",status_code=201)
def create_subscription(payload:SubscriptionIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    customer=db.get(Customer,payload.customer_id); plan=db.get(Plan,payload.plan_id)
    if not customer or not plan or not plan.is_active: raise HTTPException(400,"Invalid customer or plan")
    if payload.quantity < plan.minimum_quantity: raise HTTPException(400,"Quantity is below plan minimum")
    if plan.available_from and datetime.now(timezone.utc).date().isoformat()<plan.available_from: raise HTTPException(400,"Plan is not available yet")
    if plan.available_until and datetime.now(timezone.utc).date().isoformat()>plan.available_until: raise HTTPException(400,"Plan is no longer available")
    sub=Subscription(number=f"SUB-{uuid4().hex[:10].upper()}",customer_id=customer.id,plan_id=plan.id,status="draft",start_date=payload.start_date,expiry_date=payload.expiry_date,next_billing_date=payload.start_date,quantity=payload.quantity,payment_terms_days=payload.payment_terms_days,billing_anchor_day=payload.start_date.day)
    db.add(sub); db.flush()
    lines=payload.items
    if not lines:
        # Plan-only subscription is valid; amount is plan price x quantity at invoice time.
        pass
    else:
        for line in lines:
            product=db.get(Product,line.product_id)
            if not product or not product.is_active: raise HTTPException(400,"Invalid or inactive product")
            price=line.unit_price if line.unit_price is not None else product.sales_price
            if line.variant_id:
                variant=db.get(ProductVariant,line.variant_id)
                if not variant or variant.product_id!=product.id: raise HTTPException(400,"Invalid product variant")
                if line.unit_price is None: price+=variant.additional_price
            tax_rate=line.tax_rate
            if tax_rate is None:
                default_tax=db.scalar(select(Tax).where(Tax.is_active.is_(True)).order_by(Tax.id).limit(1))
                tax_rate=default_tax.rate if default_tax else Decimal("0")
            sub.items.append(SubscriptionItem(product_id=product.id,variant_id=line.variant_id,description=product.name,quantity=line.quantity,unit_price=price,tax_rate=tax_rate))
    audit(db,user,"subscription.created","subscription",sub.number); db.commit(); db.refresh(sub); return sub

@router.post("/subscriptions/request",status_code=201)
def request_subscription(payload:SubscriptionRequestIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if user.role!=UserRole.CUSTOMER: raise HTTPException(403,"Customer account required")
    customer_id=customer_scope(db,user)
    plan=db.get(Plan,payload.plan_id)
    today=payload.start_date
    if not plan or not plan.is_active: raise HTTPException(404,"Plan not found or unavailable")
    if payload.quantity<plan.minimum_quantity: raise HTTPException(400,"Quantity is below plan minimum")
    if plan.available_from and today.isoformat()<plan.available_from: raise HTTPException(400,"Plan is not available yet")
    if plan.available_until and today.isoformat()>plan.available_until: raise HTTPException(400,"Plan is no longer available")
    sub=Subscription(number=f"SUB-{uuid4().hex[:10].upper()}",customer_id=customer_id,plan_id=plan.id,status="draft",start_date=today,next_billing_date=today,quantity=payload.quantity,billing_anchor_day=today.day)
    db.add(sub); db.flush(); audit(db,user,"subscription.requested","subscription",sub.number)
    db.commit(); db.refresh(sub)
    return {"id":sub.id,"number":sub.number,"status":sub.status,"plan_id":sub.plan_id,"quantity":sub.quantity}

@router.get("/subscriptions")
def subscriptions(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db:Session=Depends(get_db),user:User=Depends(current_user),status_filter:str|None=None,customer_id:int|None=None):
    stmt=select(Subscription).order_by(Subscription.id.desc())
    cid=customer_scope(db,user)
    if cid: stmt=stmt.where(Subscription.customer_id==cid)
    elif customer_id is not None: stmt=stmt.where(Subscription.customer_id==customer_id)
    if status_filter: stmt=stmt.where(Subscription.status==status_filter)
    return db.scalars(stmt.limit(limit).offset(offset)).all()

@router.get("/subscriptions/{subscription_id}")
def subscription_detail(subscription_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    s=db.get(Subscription,subscription_id)
    if not s: raise HTTPException(404,"Subscription not found")
    ensure_customer_access(db,user,s.customer_id)
    return {"id":s.id,"number":s.number,"customer_id":s.customer_id,"plan_id":s.plan_id,"status":s.status,"start_date":s.start_date,"expiry_date":s.expiry_date,"next_billing_date":s.next_billing_date,"quantity":s.quantity,"items":[{"product_id":i.product_id,"description":i.description,"quantity":i.quantity,"unit_price":i.unit_price} for i in s.items]}

@router.post("/subscriptions/{sid}/action/{action}")
def subscription_action(sid:int,action:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    s=db.get(Subscription,sid)
    if not s: raise HTTPException(404,"Subscription not found")
    ensure_customer_access(db,user,s.customer_id)
    plan=db.get(Plan,s.plan_id)
    if user.role==UserRole.CUSTOMER and action not in ("pause","resume","close"): raise HTTPException(403,"Action not allowed")
    previous_expiry=s.expiry_date
    if action=="quotation":
        if user.role==UserRole.CUSTOMER or s.status!="draft": raise HTTPException(409,"Only draft subscriptions can become quotations")
        s.status="quotation"
    elif action=="confirm":
        if user.role==UserRole.CUSTOMER or s.status not in ("draft","quotation"): raise HTTPException(409,"Subscription cannot be confirmed")
        s.status="confirmed"
    elif action=="activate":
        if user.role==UserRole.CUSTOMER or s.status!="confirmed": raise HTTPException(409,"Only confirmed subscriptions can be activated")
        if not plan or not plan.is_active: raise HTTPException(409,"The subscription plan is no longer active")
        s.status="active"
    elif action=="pause":
        if not plan.allow_pause or s.status!="active": raise HTTPException(409,"Pause is not permitted")
        s.status="paused"; s.paused_at=datetime.now(timezone.utc)
    elif action=="resume":
        if not plan.allow_pause or s.status!="paused": raise HTTPException(409,"Only pausable subscriptions can resume")
        paused_days=max(0,(datetime.now(timezone.utc).date()-s.paused_at.date()).days) if s.paused_at else 0
        if s.next_billing_date: s.next_billing_date += timedelta(days=paused_days)
        if s.expiry_date: s.expiry_date += timedelta(days=paused_days)
        s.status="active"; s.paused_at=None
    elif action=="close":
        if not plan.allow_early_close or s.status not in ("active","paused","confirmed"): raise HTTPException(409,"Early closure is not permitted")
        s.status="closed"; s.closed_at=datetime.now(timezone.utc)
    elif action=="renew":
        if not plan.allow_renewal or s.status not in ("active","expired"): raise HTTPException(409,"Renewal is not permitted")
        if s.status=="expired":
            s.status="active"; s.start_date=datetime.now(timezone.utc).date(); s.next_billing_date=datetime.now(timezone.utc).date()
            s.expiry_date=next_date(datetime.now(timezone.utc).date(),plan.billing_interval,s.billing_anchor_day)
        else:
            anchor=max(s.expiry_date or s.next_billing_date or datetime.now(timezone.utc).date(),datetime.now(timezone.utc).date())
            s.expiry_date=next_date(anchor,plan.billing_interval,s.billing_anchor_day) if s.expiry_date else None
            s.next_billing_date=max(s.next_billing_date or datetime.now(timezone.utc).date(),datetime.now(timezone.utc).date())
    elif action=="expire":
        if user.role==UserRole.CUSTOMER: raise HTTPException(403,"Only staff can expire subscriptions")
        if not s.expiry_date or s.expiry_date>=datetime.now(timezone.utc).date() or s.status not in ("active","paused"):
            raise HTTPException(409,"Subscription is not eligible to expire")
        s.status="expired"; s.closed_at=datetime.now(timezone.utc)
    else: raise HTTPException(400,"Unknown subscription action")
    audit(db,user,f"subscription.{action}","subscription",s.number,{"previous_expiry_date":str(previous_expiry) if previous_expiry else None,"next_billing_date":str(s.next_billing_date),"expiry_date":str(s.expiry_date) if s.expiry_date else None}); db.commit(); db.refresh(s); return {"id":s.id,"status":s.status,"next_billing_date":s.next_billing_date}

@router.post("/taxes",status_code=201)
def create_tax(payload:TaxIn,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    obj=Tax(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/taxes")
def list_taxes(db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    return db.scalars(select(Tax).where(Tax.is_active.is_(True))).all()


@router.patch("/taxes/{tax_id}")
def update_tax(tax_id:int,payload:TaxIn,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(Tax,tax_id)
    if not item: raise HTTPException(404,"Tax not found")
    item.name=payload.name; item.rate=payload.rate
    audit(db,user,"tax.updated","tax",item.id); db.commit(); db.refresh(item); return item

@router.delete("/taxes/{tax_id}",status_code=204)
def deactivate_tax(tax_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(Tax,tax_id)
    if not item: raise HTTPException(404,"Tax not found")
    item.is_active=False; audit(db,user,"tax.deactivated","tax",item.id); db.commit(); return None

@router.post("/discounts",status_code=201)
def create_discount(payload:DiscountIn,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    if payload.kind not in ("fixed","percentage"): raise HTTPException(400,"kind must be fixed or percentage")
    if payload.kind=="percentage" and payload.value>100: raise HTTPException(400,"Percentage cannot exceed 100")
    if payload.ends_at and payload.starts_at and payload.ends_at<payload.starts_at: raise HTTPException(400,"Discount end date must be on or after its start date")
    obj=Discount(**payload.model_dump()); db.add(obj); audit(db,user,"discount.created","discount",payload.name); db.commit(); db.refresh(obj); return obj


@router.patch("/discounts/{discount_id}")
def update_discount(discount_id:int,payload:DiscountIn,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(Discount,discount_id)
    if not item: raise HTTPException(404,"Discount not found")
    if payload.kind not in ("fixed","percentage"): raise HTTPException(400,"kind must be fixed or percentage")
    if payload.kind=="percentage" and payload.value>100: raise HTTPException(400,"Percentage cannot exceed 100")
    if payload.ends_at and payload.starts_at and payload.ends_at<payload.starts_at: raise HTTPException(400,"Discount end date must be on or after its start date")
    for key,value in payload.model_dump().items(): setattr(item,key,value)
    audit(db,user,"discount.updated","discount",item.id); db.commit(); db.refresh(item); return item

@router.delete("/discounts/{discount_id}",status_code=204)
def deactivate_discount(discount_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(Discount,discount_id)
    if not item: raise HTTPException(404,"Discount not found")
    item.is_active=False; audit(db,user,"discount.deactivated","discount",item.id); db.commit(); return None

@router.get("/discounts")
def list_discounts(db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    return db.scalars(select(Discount).order_by(Discount.id.desc())).all()

def calculate_discount(db, subtotal, quantity, product_id=None):
    today=datetime.now(timezone.utc).date()
    stmt=select(Discount).where(Discount.is_active.is_(True))
    if product_id is None:
        stmt=stmt.where(Discount.product_id.is_(None))
    else:
        stmt=stmt.where(Discount.product_id==product_id)
    rules=db.scalars(stmt.order_by(Discount.id).with_for_update()).all()
    for d in rules:
        if d.starts_at and today<d.starts_at: continue
        if d.ends_at and today>d.ends_at: continue
        if d.max_uses is not None and d.used_count>=d.max_uses: continue
        if subtotal<d.min_purchase or quantity<d.min_quantity: continue
        amount=money(d.value if d.kind=="fixed" else subtotal*d.value/100)
        amount=min(amount,subtotal)
        if amount>0:
            return d,amount
    return None,Decimal("0")

def build_invoice(db,sub,period_start,today):
    existing=db.scalar(select(Invoice).where(Invoice.subscription_id==sub.id,Invoice.billing_period_start==period_start))
    if existing: return existing,False
    plan=db.get(Plan,sub.plan_id)
    inv=Invoice(number=f"INV-{uuid4().hex[:10].upper()}",customer_id=sub.customer_id,subscription_id=sub.id,billing_period_start=period_start,invoice_date=today,due_date=today+timedelta(days=sub.payment_terms_days),status="confirmed")
    db.add(inv); db.flush()
    gross_subtotal=Decimal("0"); product_discount_total=Decimal("0"); total_quantity=0
    line_bases=[]
    if sub.items:
        for item in sub.items:
            quantity=item.quantity*sub.quantity
            base=money(item.unit_price*quantity)
            product_discount,discount_amount=calculate_discount(db,base,quantity,item.product_id)
            net_base=money(base-discount_amount)
            if product_discount:
                product_discount.used_count+=1
                product_discount_total+=discount_amount
            gross_subtotal+=base; total_quantity+=quantity
            line_bases.append({"description":item.description,"quantity":quantity,"unit_price":item.unit_price,"tax_rate":item.tax_rate,"gross":base,"net":net_base,"product_discount":discount_amount})
    else:
        quantity=sub.quantity
        base=money(plan.price*quantity)
        gross_subtotal=base; total_quantity=quantity
        default_tax=db.scalar(select(Tax).where(Tax.is_active.is_(True)).order_by(Tax.id).limit(1))
        line_bases.append({"description":plan.name,"quantity":quantity,"unit_price":plan.price,"tax_rate":default_tax.rate if default_tax else Decimal("0"),"gross":base,"net":base,"product_discount":Decimal("0")})
    after_product_discounts=sum((line["net"] for line in line_bases),Decimal("0"))
    global_discount,global_discount_amount=calculate_discount(db,after_product_discounts,total_quantity,None)
    if global_discount:
        global_discount.used_count+=1
    # Allocate the subscription-wide discount proportionally, with rounding residue assigned to the final line.
    remaining_global=global_discount_amount
    remaining_base=after_product_discounts
    tax_total=Decimal("0"); discount_total=product_discount_total+global_discount_amount
    for index,line in enumerate(line_bases):
        if index==len(line_bases)-1:
            allocated=remaining_global
        elif remaining_base>0:
            allocated=money(global_discount_amount*line["net"]/after_product_discounts) if after_product_discounts else Decimal("0")
            allocated=min(allocated,line["net"],remaining_global)
        else:
            allocated=Decimal("0")
        remaining_global-=allocated
        remaining_base-=line["net"]
        taxable=money(line["net"]-allocated)
        tax=money(taxable*line["tax_rate"]/100)
        tax_total+=tax
        inv.items.append(InvoiceItem(description=line["description"],quantity=line["quantity"],unit_price=line["unit_price"],tax_rate=line["tax_rate"],discount_amount=money(line["product_discount"]+allocated),line_total=money(taxable+tax)))
    inv.subtotal=money(gross_subtotal)
    inv.tax_total=money(tax_total)
    inv.discount_total=money(discount_total)
    inv.total=max(Decimal("0"),money(gross_subtotal-discount_total+tax_total))
    return inv,True

@router.post("/billing/run")
def run_billing(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    today=datetime.now(timezone.utc).date()
    expiring=db.scalars(select(Subscription).where(Subscription.status=="active",Subscription.expiry_date<today).with_for_update()).all()
    for item in expiring:
        plan_for_item=db.get(Plan,item.plan_id)
        item.status="closed" if plan_for_item and plan_for_item.auto_close else "expired"
        item.closed_at=datetime.now(timezone.utc)
        audit(db,None,f"subscription.{item.status}","subscription",item.number,{"reason":"expiry_date_elapsed"})
    due=db.scalars(select(Subscription).where(Subscription.status=="active",Subscription.next_billing_date<=today).with_for_update()).all()
    created=[]; skipped=0
    for sub in due:
        if sub.expiry_date and sub.expiry_date<today:
            plan=db.get(Plan,sub.plan_id)
            sub.status="closed" if plan and plan.auto_close else "expired"
            sub.closed_at=datetime.now(timezone.utc)
            audit(db,None,f"subscription.{sub.status}","subscription",sub.number,{"reason":"expiry_date_elapsed"})
            continue
        start=sub.next_billing_date or today
        try:
            inv,new=build_invoice(db,sub,start,today)
            if new:
                created.append(inv.number)
                plan=db.get(Plan,sub.plan_id)
                sub.next_billing_date=next_date(start,plan.billing_interval,sub.billing_anchor_day)
                db.add(BillingCycle(subscription_id=sub.id,period_start=start,period_end=sub.next_billing_date-timedelta(days=1),invoice_id=inv.id,state="processed"))
            else: skipped+=1
        except Exception:
            db.rollback()
            raise
    audit(db,user,"billing.run","billing","manual",{"created":created,"skipped":skipped})
    db.commit()
    return {"created_count":len(created),"invoice_numbers":created,"already_processed":skipped}

@router.post("/billing/qstash")
async def qstash_billing(request:Request,db:Session=Depends(get_db)):
    # Verify signed QStash request before allowing a billing job.
    current=settings.qstash_current_signing_key; nxt=settings.qstash_next_signing_key
    if not current or not nxt: raise HTTPException(503,"QStash signing keys are not configured")
    from qstash import Receiver
    signature=request.headers.get("Upstash-Signature")
    body=(await request.body()).decode()
    if not signature: raise HTTPException(401,"Missing QStash signature")
    try:
        Receiver(current_signing_key=current,next_signing_key=nxt).verify(body=body,signature=signature,url=str(request.url),clock_tolerance=5)
    except Exception: raise HTTPException(401,"Invalid QStash signature")
    today=datetime.now(timezone.utc).date()
    expiring=db.scalars(select(Subscription).where(Subscription.status=="active",Subscription.expiry_date<today).with_for_update()).all()
    for item in expiring:
        plan_for_item=db.get(Plan,item.plan_id)
        item.status="closed" if plan_for_item and plan_for_item.auto_close else "expired"
        item.closed_at=datetime.now(timezone.utc)
        audit(db,None,f"subscription.{item.status}","subscription",item.number,{"reason":"expiry_date_elapsed"})
    due=db.scalars(select(Subscription).where(Subscription.status=="active",Subscription.next_billing_date<=today).with_for_update()).all()
    created=[]
    for sub in due:
        inv,new=build_invoice(db,sub,sub.next_billing_date or today,today)
        if new:
            created.append(inv.number); plan=db.get(Plan,sub.plan_id)
            old=sub.next_billing_date or today; sub.next_billing_date=next_date(old,plan.billing_interval,sub.billing_anchor_day)
            db.add(BillingCycle(subscription_id=sub.id,period_start=old,period_end=sub.next_billing_date-timedelta(days=1),invoice_id=inv.id,state="processed"))
    audit(db,None,"billing.run","billing","qstash",{"created":created})
    db.commit(); return {"created":created}

@router.get("/invoices")
def list_invoices(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db:Session=Depends(get_db),user:User=Depends(current_user),status_filter:str|None=None,customer_id:int|None=None,date_from:date|None=None,date_to:date|None=None):
    stmt=select(Invoice).order_by(Invoice.id.desc())
    cid=customer_scope(db,user)
    if cid: stmt=stmt.where(Invoice.customer_id==cid)
    elif customer_id is not None: stmt=stmt.where(Invoice.customer_id==customer_id)
    if date_from: stmt=stmt.where(Invoice.invoice_date>=date_from)
    if date_to: stmt=stmt.where(Invoice.invoice_date<=date_to)
    today=datetime.now(timezone.utc).date()
    if status_filter=="overdue": stmt=stmt.where(Invoice.due_date<today,Invoice.total>Invoice.amount_paid,Invoice.status.notin_(["paid","cancelled"]))
    elif status_filter: stmt=stmt.where(Invoice.status==status_filter)
    rows=db.scalars(stmt.limit(limit).offset(offset)).all()
    return [{"id":i.id,"number":i.number,"customer_id":i.customer_id,"subscription_id":i.subscription_id,"invoice_date":i.invoice_date,"due_date":i.due_date,"status":"overdue" if i.status not in ("paid","cancelled") and i.due_date<today and i.total>i.amount_paid else i.status,"subtotal":i.subtotal,"tax_total":i.tax_total,"discount_total":i.discount_total,"total":i.total,"amount_paid":i.amount_paid,"outstanding":money(i.total-i.amount_paid)} for i in rows]

@router.post("/invoices/{invoice_id}/confirm")
def confirm_invoice(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.status!="draft": raise HTTPException(409,"Only draft invoices can be confirmed")
    inv.status="confirmed"; audit(db,user,"invoice.confirmed","invoice",inv.number); db.commit(); return {"status":inv.status}

@router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.amount_paid>0: raise HTTPException(409,"Refund or reconcile payments before cancellation")
    inv.status="cancelled"; audit(db,user,"invoice.cancelled","invoice",inv.number); db.commit(); return {"status":inv.status}

@router.post("/invoices/{invoice_id}/payments",status_code=201)
def record_payment(invoice_id:int,payload:PaymentIn,idempotency_key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128),db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    prior=db.scalar(select(Payment).where(Payment.idempotency_key==idempotency_key))
    if prior:
        if prior.invoice_id != invoice_id: raise HTTPException(409,"Idempotency key was already used for another invoice")
        prior_invoice=db.get(Invoice,prior.invoice_id)
        return {"id":prior.id,"amount":prior.amount,"invoice_status":prior_invoice.status,"outstanding":money(prior_invoice.total-prior_invoice.amount_paid),"duplicate":True}
    inv=db.scalar(select(Invoice).where(Invoice.id==invoice_id).with_for_update())
    if not inv: raise HTTPException(404,"Invoice not found")
    # Re-check after the invoice lock: another request may have committed while this one waited.
    prior=db.scalar(select(Payment).where(Payment.idempotency_key==idempotency_key))
    if prior:
        if prior.invoice_id != invoice_id: raise HTTPException(409,"Idempotency key was already used for another invoice")
        return {"id":prior.id,"amount":prior.amount,"invoice_status":inv.status,"outstanding":money(inv.total-inv.amount_paid),"duplicate":True}
    if payload.method not in ("cash","bank_transfer","upi","card","razorpay"): raise HTTPException(400,"Unsupported payment method")
    if inv.status in ("cancelled","draft"): raise HTTPException(409,"Invoice is not payable")
    amount=money(payload.amount)
    if amount<=0: raise HTTPException(400,"Payment amount must be positive")
    if amount>money(inv.total-inv.amount_paid): raise HTTPException(400,"Payment exceeds outstanding balance")
    if payload.reference and db.scalar(select(Payment).where(Payment.reference==payload.reference)): raise HTTPException(409,"Payment reference already recorded")
    p=Payment(invoice_id=inv.id,method=payload.method,amount=amount,reference=payload.reference,idempotency_key=idempotency_key,note=payload.note,verified=True)
    db.add(p); inv.amount_paid=money(inv.amount_paid+amount)
    inv.status="paid" if inv.amount_paid>=inv.total else "partially_paid"
    audit(db,user,"payment.recorded","invoice",inv.number,{"amount":str(amount),"method":payload.method})
    db.commit(); db.refresh(p); return {"id":p.id,"amount":p.amount,"invoice_status":inv.status,"outstanding":money(inv.total-inv.amount_paid)}

@router.get("/payments")
def payments(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),db:Session=Depends(get_db),user:User=Depends(current_user)):
    stmt=select(Payment).order_by(Payment.id.desc()).limit(limit).offset(offset)
    cid=customer_scope(db,user)
    if cid: stmt=stmt.join(Invoice).where(Invoice.customer_id==cid)
    return db.scalars(stmt).all()

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request:Request,db:Session=Depends(get_db)):
    secret=settings.razorpay_webhook_secret
    if not secret: raise HTTPException(503,"Razorpay webhook secret is not configured")
    body=await request.body(); signature=request.headers.get("X-Razorpay-Signature","")
    expected=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature,expected): raise HTTPException(401,"Invalid webhook signature")
    import json
    try:
        event=json.loads(body)
    except (ValueError, TypeError):
        raise HTTPException(400,"Invalid webhook payload")
    if event.get("event")!="payment.captured": return {"received":True,"processed":False}
    entity=event.get("payload",{}).get("payment",{}).get("entity",{})
    notes=entity.get("notes") or {}
    invoice_id=notes.get("invoice_id")
    payment_id=entity.get("id")
    order_id=entity.get("order_id")
    if not invoice_id or not payment_id or not order_id: return {"received":True,"processed":False}
    try:
        invoice_id=int(invoice_id)
    except (TypeError, ValueError):
        raise HTTPException(400,"Invalid invoice reference")
    inv=db.scalar(select(Invoice).where(Invoice.id==invoice_id).with_for_update())
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.status in ("cancelled","draft"): raise HTTPException(409,"Invoice is not payable")
    if not inv.razorpay_order_id or not hmac.compare_digest(inv.razorpay_order_id,str(order_id)):
        raise HTTPException(409,"Razorpay order does not match this invoice")
    if db.scalar(select(Payment).where(Payment.reference==payment_id)): return {"received":True,"duplicate":True}
    try:
        amount=Decimal(str(entity.get("amount",0)))/100
    except Exception:
        raise HTTPException(400,"Invalid captured amount")
    if amount<=0 or amount>inv.total-inv.amount_paid: raise HTTPException(400,"Invalid captured amount")
    db.add(Payment(invoice_id=inv.id,method="razorpay",amount=amount,reference=payment_id,idempotency_key=f"razorpay:{payment_id}"[:128],verified=True,note="Verified Razorpay webhook"))
    inv.amount_paid=money(inv.amount_paid+amount); inv.status="paid" if inv.amount_paid>=inv.total else "partially_paid"
    db.commit(); return {"received":True,"processed":True}

@router.get("/dashboard/summary")
def dashboard_summary(db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    active=db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status=="active")) or 0
    customers_count=db.scalar(select(func.count()).select_from(Customer)) or 0
    month_start=datetime.combine(datetime.now(timezone.utc).date().replace(day=1),datetime.min.time(),tzinfo=timezone.utc)
    new_subs=db.scalar(select(func.count()).select_from(Subscription).where(Subscription.created_at>=month_start)) or 0
    collected=db.scalar(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.paid_at>=month_start,Payment.verified.is_(True))) or 0
    outstanding=db.scalar(select(func.coalesce(func.sum(Invoice.total-Invoice.amount_paid),0)).where(Invoice.status.notin_(["paid","cancelled"]))) or 0
    overdue=db.scalar(select(func.count()).select_from(Invoice).where(Invoice.due_date<datetime.now(timezone.utc).date(),Invoice.total>Invoice.amount_paid,Invoice.status!="cancelled")) or 0
    monthly_factor=case(
        (Plan.billing_interval=="daily",Decimal("30")),
        (Plan.billing_interval=="weekly",Decimal("4.3333333333")),
        (Plan.billing_interval=="yearly",Decimal("0.0833333333")),
        else_=Decimal("1"),
    )
    mrr=db.scalar(select(func.coalesce(func.sum(Plan.price*Subscription.quantity*monthly_factor),0)).join(Subscription,Subscription.plan_id==Plan.id).where(Subscription.status=="active")) or Decimal("0")
    return {"customers":customers_count,"active_subscriptions":active,"new_subscriptions":new_subs,"mrr":money(mrr),"arr":money(mrr*12),"collected_this_month":money(collected),"outstanding":money(outstanding),"overdue_invoices":overdue}

@router.get("/reports/monthly-revenue")
def monthly_revenue(db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    rows=db.execute(select(func.to_char(Payment.paid_at,"YYYY-MM").label("month"),func.sum(Payment.amount).label("collected")).where(Payment.verified.is_(True)).group_by("month").order_by("month")).all()
    return [{"month":r.month,"collected":r.collected} for r in rows]

@router.get("/audit-logs")
def audit_logs(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.ADMIN))):
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(500)).all()

@router.post("/auth/forgot-password")
def forgot_password(payload:ResetRequest,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==payload.email.lower()))
    # Always return the same response to avoid account enumeration.
    if not settings.resend_api_key or not settings.email_from:
        if settings.environment=="development" and user:
            raw=secrets.token_urlsafe(32); digest=hashlib.sha256(raw.encode()).hexdigest()
            db.query(PasswordReset).filter(PasswordReset.user_id==user.id,PasswordReset.used_at.is_(None)).delete(synchronize_session=False)
            db.add(PasswordReset(user_id=user.id,token_hash=digest,expires_at=datetime.now(timezone.utc)+timedelta(minutes=30)))
            db.commit()
            return {"message":"If the account exists, reset instructions have been sent.","development_reset_token":raw}
        if settings.environment!="development":
            raise HTTPException(503,"Password reset email service is not configured")
        return {"message":"If the account exists, reset instructions have been sent."}
    if user:
        raw=secrets.token_urlsafe(32); digest=hashlib.sha256(raw.encode()).hexdigest()
        db.query(PasswordReset).filter(PasswordReset.user_id==user.id,PasswordReset.used_at.is_(None)).delete(synchronize_session=False)
        reset_record=PasswordReset(user_id=user.id,token_hash=digest,expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
        db.add(reset_record)
        db.commit()
        import resend
        resend.api_key=settings.resend_api_key
        try:
            resend.Emails.send({"from":settings.email_from,"to":[user.email],"subject":"Reset your Brightloop password","html":f'<p>Use this one-time link within 30 minutes:</p><a href="{settings.frontend_url}/reset-password?token={raw}">Reset password</a>'})
        except Exception as exc:
            db.delete(reset_record)
            db.commit()
            raise HTTPException(502,"Password reset email could not be delivered") from exc
    return {"message":"If the account exists, reset instructions have been sent."}

@router.post("/auth/reset-password")
def reset_password(payload:ResetConfirm,db:Session=Depends(get_db)):
    digest=hashlib.sha256(payload.token.encode()).hexdigest()
    reset=db.scalar(select(PasswordReset).where(PasswordReset.token_hash==digest,PasswordReset.used_at.is_(None)).with_for_update())
    now=datetime.now(timezone.utc)
    if not reset or reset.expires_at.replace(tzinfo=timezone.utc)<now: raise HTTPException(400,"Reset token is invalid or expired")
    user=db.get(User,reset.user_id); user.password_hash=hash_password(payload.new_password); user.token_version += 1; reset.used_at=now
    db.query(PasswordReset).filter(PasswordReset.user_id==user.id,PasswordReset.id!=reset.id,PasswordReset.used_at.is_(None)).update({PasswordReset.used_at:now},synchronize_session=False)
    db.commit(); return {"message":"Password updated"}


@router.post("/invoices/{invoice_id}/razorpay-order")
def create_razorpay_order(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    inv=db.scalar(select(Invoice).where(Invoice.id==invoice_id).with_for_update())
    if not inv: raise HTTPException(404,"Invoice not found")
    ensure_customer_access(db,user,inv.customer_id)
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(503,"Razorpay credentials are not configured")
    outstanding=money(inv.total-inv.amount_paid)
    if outstanding<=0: raise HTTPException(409,"Invoice has no outstanding balance")
    if inv.status in ("draft","cancelled"): raise HTTPException(409,"Invoice is not payable")
    import httpx
    try:
        response=httpx.post(
            "https://api.razorpay.com/v1/orders",
            auth=(settings.razorpay_key_id,settings.razorpay_key_secret),
            json={"amount":int(outstanding*100),"currency":"INR","receipt":inv.number,"notes":{"invoice_id":str(inv.id)}},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502,"Razorpay order creation failed") from exc
    order=response.json()
    inv.razorpay_order_id=order["id"]
    db.commit()
    return {"order_id":order["id"],"amount":order["amount"],"currency":order["currency"],"key_id":settings.razorpay_key_id}

@router.post("/invoices/{invoice_id}/send")
def send_invoice_email(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles(*ADMIN_STAFF))):
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    customer=db.get(Customer,inv.customer_id)
    if not settings.resend_api_key or not settings.email_from:
        raise HTTPException(503,"Resend email credentials are not configured")
    import resend
    resend.api_key=settings.resend_api_key
    from html import escape
    html=f"<p>Hello {escape(customer.billing_name)},</p><p>Your invoice <b>{escape(inv.number)}</b> totals ₹{inv.total}. Due date: {inv.due_date}.</p>"
    try:
        resend.Emails.send({"from":settings.email_from,"to":[customer.email],"subject":f"Brightloop invoice {inv.number}","html":html})
    except Exception as exc:
        raise HTTPException(502,"Invoice email could not be delivered") from exc
    audit(db,user,"invoice.email_sent","invoice",inv.number); db.commit()
    return {"sent":True}

@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    inv=db.get(Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    ensure_customer_access(db,user,inv.customer_id)
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO
    buffer=BytesIO(); pdf=canvas.Canvas(buffer,pagesize=A4)
    pdf.setTitle(inv.number); pdf.setFont("Helvetica-Bold",18); pdf.drawString(50,790,"Brightloop Software")
    pdf.setFont("Helvetica",11); pdf.drawString(50,765,f"Invoice: {inv.number}")
    pdf.drawString(50,748,f"Invoice date: {inv.invoice_date}    Due: {inv.due_date}")
    customer=db.get(Customer,inv.customer_id); pdf.drawString(50,725,f"Bill to: {customer.billing_name} ({customer.email})")
    y=680
    pdf.setFont("Helvetica-Bold",10); pdf.drawString(50,y,"Description"); pdf.drawString(340,y,"Qty"); pdf.drawString(390,y,"Unit"); pdf.drawString(480,y,"Line total")
    pdf.setFont("Helvetica",10)
    for item in inv.items:
        y-=22
        if y<80: pdf.showPage(); y=780
        pdf.drawString(50,y,item.description[:45]); pdf.drawRightString(370,y,str(item.quantity)); pdf.drawRightString(450,y,str(item.unit_price)); pdf.drawRightString(550,y,str(item.line_total))
    y-=35
    for label,value in [("Subtotal",inv.subtotal),("Tax",inv.tax_total),("Discount",inv.discount_total),("Total",inv.total),("Paid",inv.amount_paid),("Outstanding",inv.total-inv.amount_paid)]:
        y-=18; pdf.drawRightString(480,y,label); pdf.drawRightString(550,y,str(value))
    pdf.save(); buffer.seek(0)
    return StreamingResponse(buffer,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{inv.number}.pdf"'})
