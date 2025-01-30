import os

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, ReplyKeyboardRemove, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app_pay_yookassa.process_yookassa import TARIFFS, get_subscription_info, save_payment_to_db
from db.orm_models import PaymentStatusType
from keyboards.payment_keyboards import tariffs_keyboard, payment_confirmation_keyboard
from services.user import set_user_tariff

payment_router = Router()


class PaymentState(StatesGroup):
    choosing_tariff = State()
    choosing_payment = State()


@payment_router.message(Command('payment'))
async def cmd_payment(message: Message, state: FSMContext):
    await state.clear()
    # unpaid_payment = await get_unpaid_payment_ids(message.from_user.id)
    # await save_payment_to_db(message.from_user.id, unpaid_payment)
    # paid_payments = await get_paid_payments(message.from_user.id)
    # await update_user_subscription(message.from_user.id, paid_payments)

    subscription_info = await get_subscription_info(message.from_user.id)
    tariff_plan = subscription_info.get('tariff_plan')
    subscription_end_date = subscription_info.get('subscription_end_date')
    if tariff_plan == "free":
        await message.answer("У вас бесплатный тариф Free. Выберите тариф для подписки:",
                             reply_markup=tariffs_keyboard())
        await state.set_state(PaymentState.choosing_tariff)
    else:
        await message.answer(
            f"У вас действующий тариф: {TARIFFS[tariff_plan]['name']} Оплачено по {subscription_end_date}.")


@payment_router.callback_query(F.data.startswith('tariff_'), PaymentState.choosing_tariff)
async def process_option(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.delete()

    tariff = callback_query.data.split('__')[1]  # название тарифа
    name = TARIFFS[tariff].get('name')
    description = TARIFFS[tariff].get('description')
    amount = TARIFFS[tariff].get('amount')
    description_eng = TARIFFS[tariff].get('description_eng')

    await state.update_data(tariff=name)
    await state.update_data(amount=amount)
    await state.update_data(description=description)
    await state.update_data(description_eng=description_eng)
    await callback_query.message.answer(f"Вы выбрали: {description} Цена: {amount} рублей.",
                                        reply_markup=payment_confirmation_keyboard())
    await state.set_state(PaymentState.choosing_payment)


@payment_router.message(F.text == '❌ Отмена', PaymentState.choosing_payment)
async def cancel_payment(message: Message, state: FSMContext):
    await cmd_payment(message, state)


@payment_router.callback_query(F.data == 'cancel_payment', PaymentState.choosing_payment)
async def cancel_payment(callback_query: CallbackQuery, state: FSMContext):
    print("callback")
    await callback_query.message.delete()
    await cmd_payment(callback_query.message, state)


@payment_router.message(F.text == '✅ Оплатить', PaymentState.choosing_payment)
async def start_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    tariff = data.get('tariff')
    description = data.get('description')
    description_eng = data.get('description_eng')
    amount = data.get('amount')
    idle_message = await message.answer(text="Формирую платеж...", reply_markup=ReplyKeyboardRemove())
    # prices = [LabeledPrice(label="rub", amount=amount, input_type=int)]
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Оплатить {amount} XTR",
        pay=True
    )
    builder.button(
        text="Отменить покупку",
        callback_data="cancel_payment"
    )
    builder.adjust(1)
    await idle_message.delete()
    prices = [LabeledPrice(label=tariff, amount=amount * 100, )]
    await message.answer_invoice(
        title=tariff,
        description=description,
        provider_token=os.getenv("TG_YOOKASSA_TEST_TOKEN"),
        currency="RUB",
        prices=prices,
        start_parameter=description_eng.replace(" ", "-"),
        payload=description_eng,
        # Переопределяем клавиатуру
        reply_markup=builder.as_markup()
    )


@payment_router.pre_checkout_query()
async def on_pre_checkout_query(
        pre_checkout_query: PreCheckoutQuery,
):
    await pre_checkout_query.answer(ok=True)


# async def pre_checkout_query(pre_checkout: PreCheckoutQuery, message: Message):
#     await message.answer_pre_checkout_query(pre_checkout.id, ok=True)


# https://docs.aiogram.dev/en/dev-3.x/api/types/successful_payment.html#module-aiogram.types.successful_payment
@payment_router.message(F.successful_payment)
async def successful_payment(message: Message):
    total_amount = message.successful_payment.total_amount
    currency = message.successful_payment.currency
    await save_payment_to_db(telegram_id=message.from_user.id,
                             payment_data=dict(message.successful_payment),
                             status=PaymentStatusType.paid)
    await set_user_tariff(telegram_id=message.from_user.id, tariff="single_month")

    await message.answer(f"Оплата на сумму {total_amount / 100} {currency} "
                         f"подтверждена !!!",
                         message_effect_id="5104841245755180586",
                         )
