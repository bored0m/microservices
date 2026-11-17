import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_self_or_admin, CurrentUser
from app.config import settings
from app.database import get_db
from app import models, schemas

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["accounts"])


@router.get("/accounts/{userId}/invoices", response_model=List[schemas.InvoiceOut])
def get_user_invoices(
    userId: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка счетов пользователя. Доступно самому пользователю, оператору и админу."""
    require_self_or_admin(userId, current_user)

    account = db.query(models.Account).filter(models.Account.user_id == userId).first()
    if account is None:
        logger.info("Счёт для пользователя %s не найден", userId)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Лицевой счёт для данного пользователя не найден")

    invoices = (
        db.query(models.Invoice)
        .filter(models.Invoice.account_id == account.id)
        .order_by(models.Invoice.created_at.desc())
        .all()
    )
    logger.info("Пользователю %s возвращено %d счетов", userId, len(invoices))
    return invoices


@router.post("/accounts", response_model=schemas.AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: schemas.AccountCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание лицевого счёта. Служебный/административный endpoint."""
    if current_user.role != "admin" and current_user.id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    existing = db.query(models.Account).filter(models.Account.user_id == payload.user_id).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Счёт для этого пользователя уже существует")

    account = models.Account(user_id=payload.user_id, currency=payload.currency)
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("Создан лицевой счёт %s для пользователя %s", account.id, payload.user_id)
    return account


@router.post("/accounts/{userId}/invoices", response_model=schemas.InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    userId: int,
    payload: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Выставление счёта пользователю (например, вызывается из Utility Service
    при закрытии заявки). В auth-service сейчас есть только роли
    resident/admin, поэтому доступ ограничен admin. Если в Identity Service
    позже добавят роль "operator" — расширить ADMIN_ROLES в app/auth.py.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Выставлять счета может только администратор")

    account = db.query(models.Account).filter(models.Account.user_id == userId).first()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Лицевой счёт для данного пользователя не найден")

    invoice = models.Invoice(
        account_id=account.id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    logger.info("Выставлен счёт %s на сумму %s для пользователя %s", invoice.id, payload.amount, userId)
    return invoice
