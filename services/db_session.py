# Синхронный вариант работы
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from config.db_config import settings

sync_engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
    echo=False,  # отладка
    pool_size=5,  # количество одновременных соединений
    max_overflow=10,  # разрешено создать еще 10 соединений после достижения pool_size
)

# Фабрика сессий
session_factory = sessionmaker(sync_engine)

# with sync_engine.connect() as conn:
#     res = conn.execute(text("SELECT VERSION()"))
#     # print(res.all())
#     print(res.first())
#     res = conn.execute(text("SELECT 1, 2, 3"))
#     print(res.first())

# Асинхронный вариант работы
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=False,  # отладка
    # pool_size=5,  # количество одновременных соединений
    # max_overflow=10,  # разрешено создать еще 10 соединений после достижения pool_size
)

# Фабрика сессий
async_session_factory = async_sessionmaker(async_engine)
