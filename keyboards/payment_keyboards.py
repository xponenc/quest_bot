from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app_pay_yookassa.process_yookassa import TARIFFS


def tariffs_keyboard(tariffs: dict = TARIFFS):
    builder = InlineKeyboardBuilder()
    for key, value in list(tariffs.items())[1:]:
        builder.button(text=value["name"],  # Текст кнопки
                       callback_data=f"tariff__{key}")  # callback_data
    builder.adjust(1)  # По одной кнопке в строке
    return builder.as_markup()  # Возвращаем готовую клавиатуру


# Клавиатура для подтверждения оплаты
def payment_confirmation_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Оплатить"),
                   KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,  # Клавиатура подстраивается под экран
        one_time_keyboard=True)  # Клавиатура исчезнет после выбора варианта