def login(client,email,password):
    response=client.post("/api/v1/auth/login",json={"email":email,"password":password})
    assert response.status_code==200,response.text
    assert "brightloop_access" in response.cookies
    return auth_headers(client)

def auth_headers(client):
    csrf=client.cookies.get("brightloop_csrf")
    return {"X-CSRF-Token":csrf} if csrf else {}

def test_customer_registration_and_role_restrictions(client):
    response=client.post("/api/v1/auth/register",json={"email":"buyer@example.com","full_name":"Buyer Account","password":"StrongPass123!"})
    assert response.status_code==201,response.text
    assert response.json()["role"]=="customer"
    assert client.get("/api/v1/products").status_code==403
    assert client.get("/api/v1/plans").status_code==200

def test_subscription_to_invoice_to_partial_payment(client):
    h=login(client,"admin@example.com","AdminPass123!")
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Acme Pvt Ltd","email":"billing@acme.example"})
    assert customer.status_code==201,customer.text
    product=client.post("/api/v1/products",headers=h,json={"name":"Growth License","product_type":"software","sales_price":"1200","cost_price":"300"})
    assert product.status_code==201,product.text
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Monthly Growth","billing_interval":"monthly","price":"1200","minimum_quantity":1})
    assert plan.status_code==201,plan.text
    sub=client.post("/api/v1/subscriptions",headers=h,json={"customer_id":customer.json()["id"],"plan_id":plan.json()["id"],"start_date":"2026-10-31","quantity":1,"items":[]})
    assert sub.status_code==201,sub.text
    sid=sub.json()["id"]
    assert sub.json()["status"]=="draft"
    assert client.post(f"/api/v1/subscriptions/{sid}/action/confirm",headers=h).status_code==200
    assert client.post(f"/api/v1/subscriptions/{sid}/action/activate",headers=h).status_code==200
    billing=client.post("/api/v1/billing/run",headers=h)
    assert billing.status_code==200,billing.text
    assert billing.json()["created_count"]==1
    invoices=client.get("/api/v1/invoices",headers=h)
    assert invoices.status_code==200
    invoice=invoices.json()[0]
    assert invoice["total"]=="1200.00" or float(invoice["total"])==1200
    pay=client.post(f"/api/v1/invoices/{invoice['id']}/payments",headers={**h,"Idempotency-Key":"payment-key-0001"},json={"method":"upi","amount":"500","reference":"test-payment-001"})
    assert pay.status_code==201,pay.text
    assert pay.json()["invoice_status"]=="partially_paid"
    assert float(pay.json()["outstanding"])==700.0
    summary=client.get("/api/v1/dashboard/summary",headers=h)
    assert summary.status_code==200
    assert float(summary.json()["collected_this_month"])==500.0

def test_payment_reference_is_idempotent(client):
    h=login(client,"admin@example.com","AdminPass123!")
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Test","email":"test@billing.example"}).json()
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Monthly","billing_interval":"monthly","price":"100","minimum_quantity":1}).json()
    sub=client.post("/api/v1/subscriptions",headers=h,json={"customer_id":customer["id"],"plan_id":plan["id"],"start_date":"2026-10-31"}).json()
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/confirm",headers=h)
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/activate",headers=h)
    client.post("/api/v1/billing/run",headers=h)
    inv=client.get("/api/v1/invoices",headers=h).json()[0]
    first=client.post(f"/api/v1/invoices/{inv['id']}/payments",headers={**h,"Idempotency-Key":"payment-key-0002"},json={"method":"cash","amount":"20","reference":"once-only"})
    second=client.post(f"/api/v1/invoices/{inv['id']}/payments",headers={**h,"Idempotency-Key":"payment-key-0002"},json={"method":"cash","amount":"20","reference":"once-only"})
    assert first.status_code==201
    assert second.status_code==201
    assert second.json()["duplicate"] is True

def test_quotation_conversion_requires_separate_activation(client):
    h=login(client,"admin@example.com","AdminPass123!")
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Quote Buyer","email":"quote@billing.example"}).json()
    product=client.post("/api/v1/products",headers=h,json={"name":"Quoted Service","product_type":"service","sales_price":"250","cost_price":"0"}).json()
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Quarterly Plan","billing_interval":"monthly","price":"250","minimum_quantity":1}).json()
    quote=client.post("/api/v1/quotations",headers=h,json={"customer_id":customer["id"],"plan_id":plan["id"],"validity_days":15,"items":[{"product_id":product["id"],"quantity":1}]}).json()
    converted=client.post(f"/api/v1/quotations/{quote['id']}/convert",headers=h)
    assert converted.status_code==201,converted.text
    assert converted.json()["status"]=="confirmed"
    duplicate=client.post(f"/api/v1/quotations/{quote['id']}/convert",headers=h)
    assert duplicate.status_code==409
    activated=client.post(f"/api/v1/subscriptions/{converted.json()['id']}/action/activate",headers=h)
    assert activated.status_code==200
    assert activated.json()["status"]=="active"


def test_product_discount_is_reflected_in_invoice_line_and_tax(client):
    h=login(client,"admin@example.com","AdminPass123!")
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Discount Buyer","email":"discount@billing.example"}).json()
    product=client.post("/api/v1/products",headers=h,json={"name":"Discountable Service","product_type":"service","sales_price":"100","cost_price":"0"}).json()
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Discount Plan","billing_interval":"monthly","price":"100","minimum_quantity":1}).json()
    tax=client.post("/api/v1/taxes",headers=h,json={"name":"GST","rate":"10"})
    assert tax.status_code==201,tax.text
    discount=client.post("/api/v1/discounts",headers=h,json={"name":"Product promo","kind":"percentage","value":"10","min_purchase":"0","min_quantity":1,"product_id":product["id"]})
    assert discount.status_code==201,discount.text
    sub=client.post("/api/v1/subscriptions",headers=h,json={"customer_id":customer["id"],"plan_id":plan["id"],"start_date":"2026-10-31","items":[{"product_id":product["id"],"quantity":1}]})
    assert sub.status_code==201,sub.text
    sid=sub.json()["id"]
    client.post(f"/api/v1/subscriptions/{sid}/action/confirm",headers=h)
    client.post(f"/api/v1/subscriptions/{sid}/action/activate",headers=h)
    billed=client.post("/api/v1/billing/run",headers=h)
    assert billed.status_code==200,billed.text
    invoice=client.get("/api/v1/invoices",headers=h).json()[0]
    assert float(invoice["subtotal"])==100.0
    assert float(invoice["discount_total"])==10.0
    assert float(invoice["tax_total"])==9.0
    assert float(invoice["total"])==99.0
    from app.db import SessionLocal
    from app.models import InvoiceItem
    db=SessionLocal()
    try:
        line=db.query(InvoiceItem).filter(InvoiceItem.invoice_id==invoice["id"]).one()
        assert float(line.discount_amount)==10.0
        assert float(line.line_total)==99.0
    finally:
        db.close()


def test_cookie_auth_requires_csrf_for_mutations(client):
    client.post("/api/v1/auth/login",json={"email":"admin@example.com","password":"AdminPass123!"})
    without_csrf=client.post("/api/v1/products",json={"name":"No CSRF","product_type":"service","sales_price":"1","cost_price":"0"})
    assert without_csrf.status_code==403
    h=auth_headers(client)
    with_csrf=client.post("/api/v1/products",headers=h,json={"name":"With CSRF","product_type":"service","sales_price":"1","cost_price":"0"})
    assert with_csrf.status_code==201

def test_customer_profile_patch_is_partial_and_isolated(client):
    registered=client.post("/api/v1/auth/register",json={"email":"profile@billing.example","full_name":"Profile Buyer","password":"StrongPass123!"})
    assert registered.status_code==201
    csrf=auth_headers(client)
    patch=client.patch("/api/v1/customers/me",headers=csrf,json={"company_name":"Brightloop Test Ltd"})
    assert patch.status_code==200,patch.text
    profile=client.get("/api/v1/customers/me").json()
    assert profile["email"]=="profile@billing.example"
    assert profile["company_name"]=="Brightloop Test Ltd"


def test_logout_invalidates_browser_session(client):
    login(client,"admin@example.com","AdminPass123!")
    assert client.get("/api/v1/auth/me").status_code==200
    access_cookie=client.cookies.get("brightloop_access")
    response=client.post("/api/v1/auth/logout",headers=auth_headers(client))
    assert response.status_code==204
    assert client.get("/api/v1/auth/me").status_code==401
    client.cookies.set("brightloop_access",access_cookie)
    assert client.get("/api/v1/auth/me").status_code==401

def test_password_reset_is_single_use_and_revokes_existing_sessions(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,"environment","development")
    login(client,"admin@example.com","AdminPass123!")
    old_access=client.cookies.get("brightloop_access")
    requested=client.post("/api/v1/auth/forgot-password",json={"email":"admin@example.com"})
    assert requested.status_code==200
    reset_token=requested.json()["development_reset_token"]
    changed=client.post("/api/v1/auth/reset-password",json={"token":reset_token,"new_password":"NewStrongPass123!"})
    assert changed.status_code==200
    reused=client.post("/api/v1/auth/reset-password",json={"token":reset_token,"new_password":"AnotherStrong123!"})
    assert reused.status_code==400
    client.cookies.set("brightloop_access",old_access)
    assert client.get("/api/v1/auth/me").status_code==401
    relogin=client.post("/api/v1/auth/login",json={"email":"admin@example.com","password":"NewStrongPass123!"})
    assert relogin.status_code==200

def test_customer_can_request_only_own_subscription(client):
    admin_headers=login(client,"admin@example.com","AdminPass123!")
    plan=client.post("/api/v1/plans",headers=admin_headers,json={"name":"Customer Starter","billing_interval":"monthly","price":"75","minimum_quantity":2}).json()
    registered=client.post("/api/v1/auth/register",json={"email":"subscriber@billing.example","full_name":"Subscriber Account","password":"StrongPass123!"})
    assert registered.status_code==201
    csrf=auth_headers(client)
    request=client.post("/api/v1/subscriptions/request",headers=csrf,json={"plan_id":plan["id"],"quantity":2,"start_date":"2026-10-31"})
    assert request.status_code==201,request.text
    sid=request.json()["id"]
    assert request.json()["status"]=="draft"
    assert client.post(f"/api/v1/subscriptions/{sid}/action/confirm",headers=csrf).status_code==403
    assert client.get("/api/v1/subscriptions").json()[0]["id"]==sid

def test_razorpay_webhook_checks_order_and_deduplicates(client, monkeypatch):
    import hashlib,hmac,json
    from app.core.config import settings
    from app.db import SessionLocal
    from app.models import Invoice
    h=login(client,"admin@example.com","AdminPass123!")
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Razorpay Buyer","email":"razorpay@billing.example"}).json()
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Razorpay Plan","billing_interval":"monthly","price":"100","minimum_quantity":1}).json()
    sub=client.post("/api/v1/subscriptions",headers=h,json={"customer_id":customer["id"],"plan_id":plan["id"],"start_date":"2026-10-31"}).json()
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/confirm",headers=h)
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/activate",headers=h)
    client.post("/api/v1/billing/run",headers=h)
    invoice=client.get("/api/v1/invoices",headers=h).json()[0]
    db=SessionLocal()
    try:
        row=db.get(Invoice,invoice["id"]); row.razorpay_order_id="order_test_brightloop"; db.commit()
    finally:
        db.close()
    monkeypatch.setattr(settings,"razorpay_webhook_secret","test-webhook-secret")
    event={"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_test_brightloop","order_id":"order_test_brightloop","amount":10000,"notes":{"invoice_id":str(invoice["id"])}}}}}
    body=json.dumps(event,separators=(",",":" )).encode()
    signature=hmac.new(b"test-webhook-secret",body,hashlib.sha256).hexdigest()
    headers={"X-Razorpay-Signature":signature}
    first=client.post("/api/v1/webhooks/razorpay",content=body,headers=headers)
    assert first.status_code==200,first.text
    assert first.json()["processed"] is True
    second=client.post("/api/v1/webhooks/razorpay",content=body,headers=headers)
    assert second.status_code==200
    assert second.json()["duplicate"] is True
    forged={**event,"payload":{"payment":{"entity":{"id":"pay_forged_order","order_id":"order_wrong","amount":10000,"notes":{"invoice_id":str(invoice["id"])}}}}}
    forged_body=json.dumps(forged,separators=(",",":" )).encode()
    forged_signature=hmac.new(b"test-webhook-secret",forged_body,hashlib.sha256).hexdigest()
    rejected=client.post("/api/v1/webhooks/razorpay",content=forged_body,headers={"X-Razorpay-Signature":forged_signature})
    assert rejected.status_code==409

def test_provider_endpoints_fail_clearly_without_credentials(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,"qstash_current_signing_key",None)
    monkeypatch.setattr(settings,"qstash_next_signing_key",None)
    assert client.post("/api/v1/billing/qstash",content="{}").status_code==503
    h=login(client,"admin@example.com","AdminPass123!")
    monkeypatch.setattr(settings,"resend_api_key",None)
    monkeypatch.setattr(settings,"email_from",None)
    customer=client.post("/api/v1/customers",headers=h,json={"billing_name":"Email Buyer","email":"emailbuyer@billing.example"}).json()
    plan=client.post("/api/v1/plans",headers=h,json={"name":"Email Plan","billing_interval":"monthly","price":"10","minimum_quantity":1}).json()
    sub=client.post("/api/v1/subscriptions",headers=h,json={"customer_id":customer["id"],"plan_id":plan["id"],"start_date":"2026-10-31"}).json()
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/confirm",headers=h)
    client.post(f"/api/v1/subscriptions/{sub['id']}/action/activate",headers=h)
    client.post("/api/v1/billing/run",headers=h)
    invoice=client.get("/api/v1/invoices",headers=h).json()[0]
    assert client.post(f"/api/v1/invoices/{invoice['id']}/send",headers=h).status_code==503

def test_password_reset_reports_missing_production_email_configuration(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,"environment","production")
    monkeypatch.setattr(settings,"resend_api_key",None)
    monkeypatch.setattr(settings,"email_from",None)
    response=client.post("/api/v1/auth/forgot-password",json={"email":"unknown@billing.example"})
    assert response.status_code==503
    assert "not configured" in response.json()["detail"]
