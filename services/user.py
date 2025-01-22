from datetime import datetime

from sqlalchemy import select, insert, text

from orm_models import async_session, UsersORM
from services.loggers import logger
from aiogram.types import Message


# Запись нового пользователя в таблицу users в базу данных
async def set_new_user(message: Message):
    async with async_session() as session:
        stmt = select(UsersORM).where(UsersORM.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalars().first()

        if user is None:
            # Вставляем все поля для нового пользователя
            new_user = UsersORM(
                telegram_id=message.from_user.id,
                registered_at=datetime.utcnow(),  # Устанавливаем текущую дату и время
                username=message.from_user.username,  # username пользователя Telegram
                name=message.from_user.full_name)  # Полное имя пользователя Telegram
            session.add(new_user)
            await session.commit()  # Фиксируем изменения
            logger.info(f"User {message.from_user.id} added into users")
