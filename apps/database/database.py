from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

POSTGRESQL_DATABASE_URL = 'postgresql+asyncpg://postgres:8565@localhost/healerstud_db'
engine = create_async_engine(url=POSTGRESQL_DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session