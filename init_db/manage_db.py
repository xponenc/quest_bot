from orm_models import Base
from services.db_session import sync_engine


def create_tables():
    # sync_engine.echo = False
    print(Base.metadata.tables)
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    sync_engine.echo = True


if __name__ == "__main__":
    create_tables()
