import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import CurrentUser, get_current_user, require_privileged, require_self_or_privileged
from ..clients.identity_client import IdentityUnavailable, user_exists
from ..database import get_db
from ..models import Account, Invoice, InvoiceStatus
from ..schemas import AccountCreate, AccountOut, InvoiceCreate, InvoiceOut

log = logging.getLogger("billing.accounts")
router = APIRouter(tags=["accounts"])


def _ensure_user_exists(target: uuid.UUID, caller: CurrentUser) -> None:
    """Проверка существования пользователя в Identity Service (только для чужих id —
    собственный id уже подтверждён валидным токеном)."""
    if target == caller.id:
        return
    try:
        found = user_exists(target, caller.token)
    except IdentityUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Identity service is unavailable")
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")


def _get_account(db: Session, user_id: uuid.UUID) -> Account | None:
    return db.scalar(select(Account).where(Account.user_id == user_id))


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Создание лицевого счёта. Без тела — счёт для текущего пользователя."""
    target = (data.user_id if data and data.user_id else None) or user.id
    require_self_or_privileged(user, target)
    _ensure_user_exists(target, user)

    if _get_account(db, target):
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already exists for this user")
    account = Account(user_id=target)
    db.add(account)
    try:
        db.commit()
    except IntegrityError:  # гонка двух одновременных запросов
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already exists for this user")
    log.info("Account created: account=%s user=%s by=%s", account.id, target, user.id)
    return account


@router.get("/accounts/{user_id}/invoices", response_model=list[InvoiceOut])
def list_invoices(
    user_id: uuid.UUID,
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Счета пользователя. Нет лицевого счёта — пустой список."""
    require_self_or_privileged(user, user_id)
    account = _get_account(db, user_id)
    if account is None:
        return []

    # Просроченные pending-счета переводим в overdue лениво, при чтении.
    updated = db.execute(
        update(Invoice)
        .where(
            Invoice.account_id == account.id,
            Invoice.status == InvoiceStatus.pending,
            Invoice.due_date < date.today(),
        )
        .values(status=InvoiceStatus.overdue)
    ).rowcount
    if updated:
        db.commit()
        log.info("Marked %s invoice(s) overdue for user=%s", updated, user_id)

    q = select(Invoice).where(Invoice.account_id == account.id)
    if status_filter:
        q = q.where(Invoice.status == status_filter)
    q = q.order_by(Invoice.created_at.desc(), Invoice.id).limit(limit).offset(offset)
    return db.scalars(q).all()


@router.post(
    "/accounts/{user_id}/invoices",
    response_model=InvoiceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    user_id: uuid.UUID,
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_privileged),
):
    """Выставление счёта (admin/operator). Лицевой счёт создаётся автоматически."""
    _ensure_user_exists(user_id, user)

    account = _get_account(db, user_id)
    if account is None:
        account = Account(user_id=user_id)
        db.add(account)
        try:
            db.commit()
            log.info("Account auto-created: account=%s user=%s", account.id, user_id)
        except IntegrityError:
            db.rollback()
            account = _get_account(db, user_id)

    invoice = Invoice(
        account_id=account.id,
        amount=data.amount,
        currency=account.currency,
        description=data.description,
        due_date=data.due_date,
    )
    db.add(invoice)
    db.commit()
    log.info("Invoice created: invoice=%s user=%s amount=%s by=%s", invoice.id, user_id, invoice.amount, user.id)
    return invoice
