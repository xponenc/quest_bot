import enum
from typing import Annotated, Optional

from dotenv import load_dotenv
import os
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import (Table, MetaData, Column, String, Integer, BigInteger, Text, Numeric,
                        ForeignKey, DateTime, Boolean, text, JSON, TIMESTAMP, Date)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

str_256 = Annotated[str, 256]
str_1024 = Annotated[str, 1024]
int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]

# Создание асинхронного сессионного объекта
async_session = async_sessionmaker(
    create_async_engine(url=DATABASE_URL, echo=False),
    expire_on_commit=False,
    class_=AsyncSession)


class Base(DeclarativeBase):
    type_annotation_map = {
        str_256: String(256)
    }

    repr_columns_num = 3
    repr_columns = ()

    def __repr__(self):
        columns = []
        for idx, column in enumerate(self.__table__.columns.keys()):
            if column in self.repr_columns or idx < self.repr_columns_num:
                columns.append(f"{column} = {getattr(self, column)}")
        return f"<{self.__class__.__name__} {', '.join(columns)}>"


# Association table (вспомогательная таблица для связи many-to-many)
user_game_association = Table(
    "user_game_association",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("game_id", ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
)


# описание части существующей таблицы users
class UsersORM(Base):
    __tablename__ = "users"

    # id: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[int_pk]
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str_256]
    name: Mapped[str_256]
    registered_at: Mapped[created_at]
    name: Mapped[str_256]
    tariff_plan: Mapped[str] = mapped_column(
        String, nullable=True, default="free")
    subscription_end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, default=date.today)

    games: Mapped[list["GamesORM"]] = relationship(
        "GamesORM",
        secondary=user_game_association,  # Указываем вспомогательную таблицу
        back_populates="users",  # Обратная связь
    )

    stages: Mapped[list["GameStagesORM"]] = relationship(  # Добавляем связь для stages
        "GameStagesORM",
        back_populates="user",
        foreign_keys="[GameStagesORM.user_id]",  # Указываем внешний ключ
    )


class GamesORM(Base):
    __tablename__ = "games"

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    users: Mapped[list["UsersORM"]] = relationship(
        "UsersORM",
        secondary=user_game_association,  # Указываем вспомогательную таблицу
        back_populates="games",  # Обратная связь
    )

    game_stages: Mapped[list["GameStagesORM"]] = relationship(
        "GameStagesORM",
        back_populates="game",
        foreign_keys="[GameStagesORM.game_id]",  # Указываем внешний ключ
    )


class GameStageType(enum.Enum):
    options = "options"
    dialog = "dialog"


class GameStagesORM(Base):
    __tablename__ = "game_stages"

    id: Mapped[int_pk]
    type: Mapped[GameStageType]
    data: Mapped[dict] = mapped_column(JSON)
    gamer_answer: Mapped[Optional[str_1024]]
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    created_at: Mapped[created_at]

    game: Mapped["GamesORM"] = relationship(
        "GamesORM",
        back_populates="game_stages",
        foreign_keys="[GameStagesORM.game_id]",  # Указываем правильный внешний ключ
    )

    user: Mapped[list["UsersORM"]] = relationship(
        "UsersORM",
        back_populates="stages",
    )


class PaymentStatusType(enum.Enum):
    created = "created"
    canceled = "canceled"
    paid = "paid"


class PaymentRecordORM(Base):
    __tablename__ = "payment_records"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        UsersORM.id), nullable=False)  # ID пользователя
    # payment_id: Mapped[str] = mapped_column(
    #     String(255), nullable=False)  # Уникальный ID платежа
    status: Mapped[str] = Mapped[GameStageType]
    refundable: Mapped[bool] = mapped_column(
        Boolean, nullable=True)  # Возможность возврата

    # Поля для суммы платежа
    amount_value: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True)  # Сумма платежа
    amount_currency: Mapped[str] = mapped_column(
        String, nullable=True)  # Валюта платежа

    # Поля для дохода
    income_amount_value: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True)  # Сумма дохода
    income_amount_currency: Mapped[str] = mapped_column(
        String, nullable=True)  # Валюта дохода

    description: Mapped[str | None] = mapped_column(
        String, nullable=True)  # Описание
    payment_method: Mapped[dict | None] = mapped_column(
        JSON, nullable=True)  # Метод оплаты
    recipient: Mapped[dict | None] = mapped_column(
        JSON, nullable=True)  # Получатель
    authorization_details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True)  # Авторизационные данные
    refunded_amount: Mapped[dict | None] = mapped_column(
        JSON, nullable=True)  # Данные о возврате
    metadata_payment: Mapped[dict | None] = mapped_column(
        JSON, nullable=True)  # Метаданные
    provider_payment_charge_id = Mapped[str_256 | None]
    telegram_payment_charge_id = Mapped[str_256 | None]
    created_at: Mapped[created_at]
    paid_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=True, )  # Дата завершения платежа (если оплачено)
