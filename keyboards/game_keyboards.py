from aiogram.utils.keyboard import ReplyKeyboardBuilder


def options_keyboard():
    builder = ReplyKeyboardBuilder()
    buttons = ["1",
               "2",
               "3", ]
    for button in buttons:
        builder.button(text=button)
    builder.adjust(3)  # Устанавливаем по 2 кнопки в ряд
    return builder.as_markup(
        resize_keyboard=True,  # Клавиатура подстраивается под размер экрана
        one_time_keyboard=True,  # Клавиатура исчезнет после выбора варианта
        input_field_placeholder="Выберите ход")  # Подсказка для поля ввода
