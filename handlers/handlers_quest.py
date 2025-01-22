import json

from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from keyboards.game_keyboards import options_keyboard
from orm_models import GameStageType
from services.db_process import add_new_game_to_db, add_new_gamestage_to_db, add_user_choice_to_stage
from services.gpt import gpt_create_new_game, gpt_create_new_stage
from services.loggers import logger

QUEST_COMMANDS = {
    # "games": {
    #     "name": "Все игры",
    #     "info": "1. 📚 - Посмотреть список игр"},
    "new_game": {
        "name": "Новая игра",
        "info": "2. 🧑 - Начать новую игру"},
    # "continue_game": {
    #     "name": "Продолжить игру",
    #     "info": "3. 💳 - Продолжить текущую игру"},
    # "end_game": {
    #     "name": "Завершить игру",
    #     "info": "4. ⚙️ - Завершить текущую игру"},
    # "support": {
    #     "name": "Тех. поддержка",
    #     "info": "5. 🆘 - Тех.поддержка: Обратитесь за технической поддержкой"},
}


quest_router = Router()


# Класс, описывающий состояния
class QuestState(StatesGroup):
    new_game = State()
    continue_game = State()
    end_game = State()
    choose_next_stage = State()


@quest_router.message(StateFilter(None), Command(commands=["new_game", ]))
async def main_menu(message: Message, state: FSMContext):
    logger.info(f"Start new game for user {message.from_user.id}")
    idle_message = await message.answer(
        text='Старт игры...',
        reply_markup=ReplyKeyboardRemove()  # Очистка клавиатуры
    )
    game_data, price, tokens_info = await gpt_create_new_game()
    game = json.loads(game_data.replace("`", "'").lstrip("json").strip())
    game_id = add_new_game_to_db(game_data=game, telegram_id=message.from_user.id)
    await message.answer(
        text=f"{game.get('game_name')}\n\n{game.get('story')}",
        reply_markup=ReplyKeyboardRemove()  # Очистка клавиатуры
    )
    # sent_message = await idle_message.edit_text(f"{game.get('game_name')}\n{game.get('story')}")
    options_of_moves = game.get("options_of_moves")
    stage_id = add_new_gamestage_to_db(
        game_id=game_id,
        stage_type=GameStageType.options,
        stage_data=options_of_moves,
        telegram_id=message.from_user.id)

    step_story = "\n".join(f"{key}: {value.get('description')}\t{value.get('outcome_hint')}"
                           for key, value in options_of_moves.items())
    await message.answer(
        text=f"Сделай выбор:\n{step_story}",
        reply_markup=options_keyboard())

    await state.update_data(game_id=game_id, stage_id=stage_id, stage_type=GameStageType.options,
                            options_of_moves=options_of_moves)
    await state.set_state(QuestState.choose_next_stage)


@quest_router.message(QuestState.choose_next_stage)
async def get_stage_choice(message: Message, state: FSMContext):
    choice = message.text.lstrip("/")
    user_data = await state.get_data()
    game_id = user_data.get("game_id")
    stage_type = user_data.get("stage_type")
    stage_id = user_data.get("stage_id")

    if stage_type == GameStageType.options:
        options_of_moves = user_data.get("options_of_moves")
        if choice not in "123":
            step_story = "\n".join(f"{key}: {value.get('description')}\t{value.get('outcome_hint')}"
                                   for key, value in options_of_moves.items())
            await message.answer(
                text=f"Сделай выбор:\n{step_story}",
                reply_markup=options_keyboard())
        gamer_answer = options_of_moves.get(choice).get("description")

    else:  # stage_type == GameStageType.dialog:
        gamer_answer = message.text
    logger.info(f"User {message.from_user.id} answer: {gamer_answer}")

    await message.answer(text="Выбор сделан", reply_markup=ReplyKeyboardRemove())
    await add_user_choice_to_stage(stage_id=stage_id, gamer_answer=gamer_answer)
    stage_data, price, tokens_info = await gpt_create_new_stage(
        game_id=game_id,
        telegram_id=message.from_user.id,
    )
    new_stage = json.loads(stage_data)
    stage_type = GameStageType.options if new_stage.get("options_of_moves") else GameStageType.dialog
    if stage_type == GameStageType.options:
        stage_data = new_stage.get("options_of_moves")
        step_story = "\n".join(f"{key}: {value.get('description')}\t{value.get('outcome_hint')}"
                               for key, value in stage_data.items())

        await state.update_data(options_of_moves=stage_data)
        await message.answer(
            text=f"{new_stage.get("stage_description")}:\n{step_story}",
            reply_markup=options_keyboard())
    else:
        stage_data = new_stage
        step_story = stage_data
        await message.answer(
            text=f"{step_story}",
            reply_markup=options_keyboard())

    stage_id = add_new_gamestage_to_db(
        game_id=game_id,
        stage_type=stage_type,
        stage_data=stage_data,
        telegram_id=message.from_user.id)

    await state.update_data(game_id=game_id, stage_id=stage_id, stage_type=GameStageType.options)
    await state.set_state(QuestState.choose_next_stage)
