from base64 import b64encode
import asyncio
from pprint import pprint

import aiohttp
from sqlalchemy import select, update
from datetime import datetime
from dateutil import parser  # Для гибкой обработки дат
from dateutil.relativedelta import relativedelta
# from db_start import async_session
# from db_models import PaymentRecord, User
import logging
from yookassa import Configuration, Payment
from dotenv import load_dotenv
import uuid
import os

from db.orm_models import async_session, UsersORM, PaymentStatusType, PaymentRecordORM
from services.loggers import logger

load_dotenv()
Configuration.account_id = os.getenv("YOOKASSA_TEST_SHOP")
Configuration.secret_key = os.getenv("YOOKASSA_TEST_KEY")

TARIFFS = {
    "free": {
        "name": "Free",
        "description": "Бесплатный тариф с ограниченным доступом.",
        "amount": 0,
        "duration_months": 0
    },
    "single_month": {
        "name": "1 месяц - 1900 руб.",
        "description": "Доступ на 1 месяц.",
        "description_eng": "1 month 1900rub",
        "amount": 1900,
        "duration_months": 1
    },
    "three_months": {
        "name": "3 месяца - 4900 руб. (1633 руб/мес) скидка 14%.",
        "description": "Доступ на 3 месяца.",
        "description_eng": "3 month 4900rub",

        "amount": 4900,
        "duration_months": 3
    },
    "six_months": {
        "name": "6 месяцев - 8900 руб. (1483 руб/мес) скидка 22%.",
        "description": "Доступ на 6 месяцев.",
        "description_eng": "6 month 8900rub",
        "amount": 8900,
        "duration_months": 6
    },
    "twelve_months": {
        "name": "12 месяцев - 14900 руб. (1242 руб/мес) скидка 35%.",
        "description": "Доступ на 12 месяцев.",
        "description_eng": "12 month 14900rub",
        "amount": 14900,
        "duration_months": 12
    }
}


# Получить информацию о тарифе по его описанию из TARIFFS
def tarif_info(description: str):
    for tariff, value in TARIFFS.items():
        if value["description"] == description:
            return tariff, value["name"], value["duration_months"]
    return None, None, None  # Если тариф с указанным описанием не найден


# Утилита для безопасного извлечения вложенных значений из словаря
def get_nested(data, *keys, default=None):
    for key in keys:
        data = data.get(key, {})
    return data or default


# создание словаря для записи платежей в таблицу PaymentRecord
def create_common_data(user_id, payment_data):
    return {
        "user_id": user_id,
        "status": payment_data.get("status"),
        "paid": payment_data.get("paid", False),
        "refundable": payment_data.get("refundable", False),
        "amount_value": float(get_nested(payment_data, "amount", "value", default=0.0)),
        "amount_currency": get_nested(payment_data, "amount", "currency", default=""),
        "income_amount_value": float(get_nested(payment_data, "income_amount", "value", default=0.0)),
        "income_amount_currency": get_nested(payment_data, "income_amount", "currency", default=""),
        "description": payment_data.get("description"),
        "payment_method": payment_data.get("payment_method"),
        "recipient": payment_data.get("recipient"),
        "authorization_details": payment_data.get("authorization_details"),
        "refunded_amount": payment_data.get("refunded_amount"),
        "metadata_payment": payment_data.get("metadata"),
        "captured_at": parser.isoparse(payment_data.get("captured_at")).replace(tzinfo=None)
        if payment_data.get("captured_at") else None,
        "created_at": parser.isoparse(payment_data.get("created_at")).replace(tzinfo=None),
        "test": payment_data.get("test", False),
        "confirmation": payment_data.get("confirmation")}




async def save_payment_to_db(telegram_id: int, payment_data: dict,
                             status: PaymentStatusType = PaymentStatusType.created):
    async with async_session() as session:
        stmt = select(UsersORM).where(UsersORM.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        payment = PaymentRecordORM(
            user_id=user.id,
            status=status.value,
            amount_value=payment_data.get("total_amount") / 100,
            amount_currency=payment_data.get("currency"),
            description=payment_data.get("invoice_payload"),
            metadata_payment=payment_data,
            provider_payment_charge_id=payment_data.get("provider_payment_charge_id"),
            telegram_payment_charge_id=payment_data.get("telegram_payment_charge_id"),
        )
        if status == PaymentStatusType.paid:
            payment.paid_at = datetime.utcnow()
        session.add(payment)
        await session.commit()
        logger.info(f"Добавлена запись с payment_id {payment.id} и paid={status.value}.")


# Получение информации о подписке из таблицы User
async def get_subscription_info(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(UsersORM.tariff_plan,
                   UsersORM.subscription_end_date,
                   ).where(UsersORM.telegram_id == telegram_id))
        # Получаем единственную запись или None
        subscription_info = result.one_or_none()
    if subscription_info:
        if subscription_info.subscription_end_date:
            available_time = subscription_info.subscription_end_date >= datetime.now().date()
        else:
            available_time = False
        logger.info(f"{telegram_id} - Получение информации о подписке.")
        return {"tariff_plan": subscription_info.tariff_plan if available_time else 'free',
                "subscription_end_date": subscription_info.subscription_end_date}
    return None
