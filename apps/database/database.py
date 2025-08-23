from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from env import DATABASE_NAME, USERNAME, PASSWORD, HOST

POSTGRESQL_DATABASE_URL = f'postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE_NAME}'
engine = create_async_engine(url=POSTGRESQL_DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session