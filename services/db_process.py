import json

from sqlalchemy import select

from orm_models import GamesORM, GameStagesORM, GameStageType, UsersORM
from services.db_session import async_session_factory, session_factory
from services.loggers import logger


def add_new_game_to_db(game_data: dict, telegram_id) -> int:
    """Сохраняет в ДБ новую игру"""
    with session_factory() as session:
        # Получаем пользователя по telegram_id
        user = session.scalar(select(UsersORM).where(UsersORM.telegram_id == telegram_id))
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        # Создаем новую игру
        new_game = GamesORM(
            name=game_data.get("game_name"),
            description=game_data.get("story"),
            users=[user]  # Устанавливаем связь сразу
        )

        # Добавляем новую игру и сохраняем изменения
        session.add(new_game)
        session.commit()
        logger.info(f"DB: Created new game: {new_game}")

        # Возвращаем ID игры
        return new_game.id


async def add_user_choice_to_stage(stage_id: int, gamer_answer: str):
    async with async_session_factory() as session:
        stage = await session.get(GameStagesORM, stage_id)
        stage.gamer_answer = gamer_answer
        await session.commit()
        logger.info(f"DB: Added gamer answer for game stage: {gamer_answer}")


async def get_game_context(telegram_id: int, game_id: int):
    async with async_session_factory() as session:
        game = await session.get(GamesORM, game_id)
        query = (
            select(GameStagesORM)
            .join(UsersORM, UsersORM.id == GameStagesORM.user_id)
            .where(GameStagesORM.game_id == game_id)  # Указание правильного атрибута
            .where(UsersORM.telegram_id == telegram_id)
            .order_by(GameStagesORM.created_at.asc())
        )
        result = await session.execute(query)
        # print(result.all())
        stages = result.scalars().all()
        game_context = f"{game.name}\n{game.description}\n"
        stage_context = ""

        for index, stage in enumerate(stages, start=1):
            stage_context += f"# Шаг {index}({stage.type.value}):\n"
            stage_context += "\n".join(f"{option_index}: {option_value.get('description')}"
                                       f" {option_value.get('outcome_hint')}"
                                       for option_index, option_value in stage.data.items())
            stage_context += f"\nИгрок выбрал: {stage.gamer_answer}"
        logger.info(f"DB: For game {game_id} created game context: {game_context + stage_context}")

        return game_context + stage_context


def add_new_gamestage_to_db(game_id: int, stage_type: GameStageType, stage_data: dict, telegram_id: int) -> int:
    """Сохраняет в ДБ шаг игры"""
    with session_factory() as session:
        # Получаем пользователя по telegram_id
        user = session.scalar(select(UsersORM).where(UsersORM.telegram_id == telegram_id))
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        new_stage = GameStagesORM(
            type=stage_type,
            data=stage_data,
            user_id=user.id,
            game_id=game_id
        )

        # Добавляем новую игру и сохраняем изменения
        session.add(new_stage)
        session.commit()
        logger.info(f"For game {game_id} created game stage {new_stage.id} {new_stage}")

        # Возвращаем ID игры
        return new_stage.id
