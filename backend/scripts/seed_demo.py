import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import User, UserRole, Customer, Product, ProductVariant, Plan, Subscription, Quotation, QuotationItem, Invoice, InvoiceItem, Payment, Tax, Discount
from app.core.security import hash_password

def main():
    db=SessionLocal()
    try:
        admin_email=os.getenv("DEMO_ADMIN_EMAIL","admin@brightloop.demo").lower()
        staff_email=os.getenv("DEMO_STAFF_EMAIL","staff@brightloop.demo").lower()
        customer_email=os.getenv("DEMO_CUSTOMER_EMAIL","customer@brightloop.demo").lower()
        accounts=[
            (admin_email,os.getenv("DEMO_ADMIN_PASSWORD"),"Brightloop Admin",UserRole.ADMIN),
            (staff_email,os.getenv("DEMO_STAFF_PASSWORD"),"Brightloop Staff",UserRole.STAFF),
            (customer_email,os.getenv("DEMO_CUSTOMER_PASSWORD"),"Demo Customer",UserRole.CUSTOMER),
        ]
        for email,password,name,role in accounts:
            if not password: raise RuntimeError(f"Set password env var for {email} before seeding")
            user=db.scalar(select(User).where(User.email==email))
            if not user:
                user=User(email=email,full_name=name,password_hash=hash_password(password),role=role)
                db.add(user); db.flush()
            if role==UserRole.CUSTOMER and not db.scalar(select(Customer).where(Customer.user_id==user.id)):
                db.add(Customer(user_id=user.id,billing_name=name,email=email,company_name="Brightloop Demo Customer"))
        if not db.scalar(select(Product).limit(1)):
            for name,price,cost in [
                ("Brightloop Starter",990,250),("Brightloop Growth",2490,700),
                ("Brightloop Enterprise",7990,2400),("Analytics Add-on",560,120),
                ("Priority Support",1200,350),("Extra Workspace",350,80),
                ("API Access",800,150),("Onboarding",5000,1800)]:
                p=Product(name=name,product_type="software",sales_price=price,cost_price=cost,notes="Demo catalogue item")
                db.add(p); db.flush()
                if name=="Brightloop Growth": db.add(ProductVariant(product_id=p.id,name="Odoo Brand",additional_price=560))
        if not db.scalar(select(Plan).limit(1)):
            for name,interval,price in [
                ("Daily Trial","daily",99),("Weekly Flex","weekly",499),
                ("Monthly Starter","monthly",990),("Monthly Growth","monthly",2490),
                ("Annual Growth","yearly",24900),("Annual Enterprise","yearly",79900)]:
                db.add(Plan(name=name,billing_interval=interval,price=price,minimum_quantity=1,auto_close=False,allow_early_close=True,allow_pause=True,allow_renewal=True))
        db.flush()
        # Ten customer billing profiles, including the linked portal demo account.
        customer_count=db.scalar(select(func.count()).select_from(Customer)) or 0
        for index in range(customer_count,10):
            db.add(Customer(billing_name=f"Demo Customer {index+1}",email=f"customer{index+1}@brightloop.demo",company_name=f"Demo Company {index+1}"))
        db.flush()
        customers=db.scalars(select(Customer).order_by(Customer.id)).all()
        products=db.scalars(select(Product).order_by(Product.id)).all()
        plans=db.scalars(select(Plan).order_by(Plan.id)).all()
        if not db.scalar(select(Tax).limit(1)):
            db.add(Tax(name="GST Demo",rate=Decimal("18.00")))
        if not db.scalar(select(Discount).limit(1)):
            db.add(Discount(name="Launch 10 Percent",kind="percentage",value=Decimal("10"),min_purchase=0,min_quantity=1,max_uses=100))
        if not db.scalar(select(Quotation).limit(1)) and customers and products and plans:
            quote=Quotation(number="QUO-DEMO-0001",customer_id=customers[0].id,plan_id=plans[2].id,status="quotation",valid_until=date.today()+timedelta(days=21),subtotal=products[0].sales_price,tax_total=0,discount_total=0,total=products[0].sales_price)
            db.add(quote); db.flush()
            db.add(QuotationItem(quotation_id=quote.id,product_id=products[0].id,description=products[0].name,quantity=1,unit_price=products[0].sales_price,tax_rate=0,line_total=products[0].sales_price))
        if not db.scalar(select(Subscription).limit(1)) and customers and plans:
            states=["active","active","paused","closed","confirmed","active"]
            for index,state in enumerate(states):
                start=date.today()-timedelta(days=45+index*7)
                db.add(Subscription(number=f"SUB-DEMO-{index+1:04d}",customer_id=customers[index].id,plan_id=plans[index%len(plans)].id,status=state,start_date=start,next_billing_date=date.today() if state=="active" else date.today()+timedelta(days=15),quantity=1,payment_terms_days=15,billing_anchor_day=start.day))
        db.flush()
        subscriptions=db.scalars(select(Subscription).order_by(Subscription.id)).all()
        if not db.scalar(select(Invoice).limit(1)):
            for index,sub in enumerate(subscriptions[:5]):
                plan=db.get(Plan,sub.plan_id)
                total=Decimal(plan.price)
                invoice_date=date.today()-timedelta(days=20+index*4)
                due=invoice_date+timedelta(days=15)
                status="paid" if index==0 else ("overdue" if index==1 else ("partially_paid" if index==2 else "confirmed"))
                paid=total if status=="paid" else (total/2 if status=="partially_paid" else Decimal("0"))
                inv=Invoice(number=f"INV-DEMO-{index+1:04d}",customer_id=sub.customer_id,subscription_id=sub.id,billing_period_start=invoice_date,invoice_date=invoice_date,due_date=due,status=status,subtotal=total,tax_total=0,discount_total=0,total=total,amount_paid=paid)
                db.add(inv); db.flush()
                db.add(InvoiceItem(invoice_id=inv.id,description=plan.name,quantity=1,unit_price=total,tax_rate=0,line_total=total))
                if paid>0:
                    db.add(Payment(invoice_id=inv.id,method="upi",amount=paid,reference=f"DEMO-PAY-{index+1:04d}",verified=True,note="Seeded demo payment"))
        db.commit()
        print("Demo seed complete: demo roles, 10 customers, 8 products, variants, 6 plans, quotations, subscriptions, invoices and payments persisted.")
    finally: db.close()

if __name__=="__main__": main()
