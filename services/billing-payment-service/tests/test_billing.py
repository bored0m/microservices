import uuid
from datetime import date, timedelta

from sqlalchemy import text

from app.database import engine

from .conftest import WEBHOOK_HEADERS, make_token

INVOICE = {"amount": "1500.00", "description": "Вывоз мусора", "due_date": "2099-01-01"}


def issue_invoice(client, operator, user_id, **override):
    _, op_h = operator
    r = client.post(f"/accounts/{user_id}/invoices", json={**INVOICE, **override}, headers=op_h)
    assert r.status_code == 201, r.text
    return r.json()


def pay(client, headers, invoice_id, method="card"):
    return client.post("/payments", json={"invoice_id": invoice_id, "method": method}, headers=headers)


def webhook(client, **body):
    return client.post("/payments/webhook/success", json=body, headers=WEBHOOK_HEADERS)


# ---------- auth ----------
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_no_token_401(client):
    assert client.get(f"/accounts/{uuid.uuid4()}/invoices").status_code == 401


def test_bad_token_401(client):
    r = client.get(f"/accounts/{uuid.uuid4()}/invoices", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


def test_non_uuid_sub_401(client):
    import jwt

    token = jwt.encode({"sub": "42"}, "test-jwt-secret", algorithm="HS256")
    r = client.get(f"/accounts/{uuid.uuid4()}/invoices", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# ---------- accounts / invoices ----------
def test_list_invoices_without_account_is_empty(client, user):
    uid, h = user
    assert client.get(f"/accounts/{uid}/invoices", headers=h).json() == []


def test_create_account_self_and_conflict(client, user):
    _, h = user
    assert client.post("/accounts", headers=h).status_code == 201
    assert client.post("/accounts", headers=h).status_code == 409


def test_create_account_for_other_forbidden_for_resident(client, user):
    _, h = user
    r = client.post("/accounts", json={"user_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 403


def test_resident_cannot_issue_invoice(client, user):
    uid, h = user
    r = client.post(f"/accounts/{uid}/invoices", json=INVOICE, headers=h)
    assert r.status_code == 403


def test_issue_and_list_invoices(client, user, operator):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    assert inv["status"] == "pending" and inv["amount"] == "1500.00"
    listed = client.get(f"/accounts/{uid}/invoices", headers=h).json()
    assert [i["id"] for i in listed] == [inv["id"]]
    assert client.get(f"/accounts/{uid}/invoices?status=paid", headers=h).json() == []


def test_other_user_cannot_read_invoices(client, user, operator):
    uid, _ = user
    issue_invoice(client, operator, uid)
    _, other_h = make_token()
    assert client.get(f"/accounts/{uid}/invoices", headers=other_h).status_code == 403
    # оператор — может
    assert client.get(f"/accounts/{uid}/invoices", headers=operator[1]).status_code == 200


def test_invoice_validation_422(client, user, operator):
    uid, _ = user
    _, op_h = operator
    for bad in ({"amount": "0"}, {"amount": "-5"}, {"amount": "10.999"}, {"due_date": "not-a-date"}):
        r = client.post(f"/accounts/{uid}/invoices", json={**INVOICE, **bad}, headers=op_h)
        assert r.status_code == 422, bad


def test_pending_past_due_becomes_overdue(client, user, operator):
    uid, h = user
    issue_invoice(client, operator, uid, due_date=str(date.today() - timedelta(days=1)))
    assert client.get(f"/accounts/{uid}/invoices", headers=h).json()[0]["status"] == "overdue"


# ---------- payments ----------
def test_full_payment_flow(client, user, operator, sent_notifications):
    uid, h = user
    inv = issue_invoice(client, operator, uid)

    r = pay(client, h, inv["id"])
    assert r.status_code == 201
    p = r.json()
    assert p["status"] == "processing" and p["amount"] == "1500.00" and p["provider_ref"]

    r = webhook(client, provider_ref=p["provider_ref"], status="succeeded", amount="1500.00")
    assert r.status_code == 200 and r.json()["status"] == "processed"

    assert client.get(f"/payments/{p['id']}", headers=h).json()["status"] == "succeeded"
    assert client.get(f"/accounts/{uid}/invoices", headers=h).json()[0]["status"] == "paid"
    assert len(sent_notifications) == 1 and sent_notifications[0][0] == uid


def test_webhook_is_idempotent(client, user, operator, sent_notifications):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    ref = pay(client, h, inv["id"]).json()["provider_ref"]
    assert webhook(client, provider_ref=ref).json()["status"] == "processed"
    assert webhook(client, provider_ref=ref).json()["status"] == "already_processed"
    assert len(sent_notifications) == 1  # повторное уведомление не уходит
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM payment_webhook_events WHERE processed")).scalar() == 2


def test_cannot_pay_twice(client, user, operator, sent_notifications):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    ref = pay(client, h, inv["id"]).json()["provider_ref"]
    # пока платёж в процессе — второй запрещён
    assert pay(client, h, inv["id"]).status_code == 409
    webhook(client, provider_ref=ref)
    # после оплаты — тоже
    assert pay(client, h, inv["id"]).status_code == 409


def test_cannot_pay_foreign_invoice(client, user, operator):
    uid, _ = user
    inv = issue_invoice(client, operator, uid)
    _, other_h = make_token()
    assert pay(client, other_h, inv["id"]).status_code == 403


def test_pay_unknown_invoice_404(client, user):
    assert pay(client, user[1], str(uuid.uuid4())).status_code == 404


def test_pay_cancelled_invoice_409(client, user, operator):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    with engine.begin() as c:
        c.execute(text("UPDATE invoices SET status='cancelled'"))
    assert pay(client, h, inv["id"]).status_code == 409


def test_pay_invalid_method_422(client, user, operator):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    assert pay(client, h, inv["id"], method="bitcoin").status_code == 422


def test_get_foreign_payment_403(client, user, operator):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    pid = pay(client, h, inv["id"]).json()["id"]
    assert client.get(f"/payments/{pid}", headers=make_token()[1]).status_code == 403
    assert client.get(f"/payments/{uuid.uuid4()}", headers=h).status_code == 404


# ---------- webhook security & edge cases ----------
def test_webhook_requires_secret(client):
    r = client.post("/payments/webhook/success", json={"provider_ref": "x"})
    assert r.status_code == 401
    r = client.post("/payments/webhook/success", json={"provider_ref": "x"}, headers={"X-Webhook-Secret": "nope"})
    assert r.status_code == 401


def test_webhook_user_jwt_is_not_enough(client, user):
    r = client.post("/payments/webhook/success", json={"provider_ref": "x"}, headers=user[1])
    assert r.status_code == 401


def test_webhook_unknown_provider_ref_404_and_logged(client):
    assert webhook(client, provider_ref="sim_unknown").status_code == 404
    with engine.connect() as c:
        row = c.execute(text("SELECT payment_id, processed FROM payment_webhook_events")).one()
    assert row.payment_id is None and row.processed is False


def test_webhook_amount_mismatch_409_state_unchanged(client, user, operator, sent_notifications):
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    p = pay(client, h, inv["id"]).json()
    assert webhook(client, provider_ref=p["provider_ref"], amount="1.00").status_code == 409
    assert client.get(f"/payments/{p['id']}", headers=h).json()["status"] == "processing"
    assert client.get(f"/accounts/{uid}/invoices", headers=h).json()[0]["status"] == "pending"
    assert sent_notifications == []


def test_webhook_bad_body_422(client):
    assert webhook(client).status_code == 422
    assert webhook(client, provider_ref="x", status="failed").status_code == 422


def test_notification_failure_does_not_break_payment(client, user, operator, monkeypatch):
    """Notification Service недоступен — вебхук всё равно успешен."""
    monkeypatch.setenv("BILLING_NOTIFICATION_SERVICE_URL", "http://127.0.0.1:1")
    from app.config import get_settings

    get_settings.cache_clear()
    uid, h = user
    inv = issue_invoice(client, operator, uid)
    ref = pay(client, h, inv["id"]).json()["provider_ref"]
    assert webhook(client, provider_ref=ref).status_code == 200
    assert client.get(f"/accounts/{uid}/invoices", headers=h).json()[0]["status"] == "paid"
    get_settings.cache_clear()
