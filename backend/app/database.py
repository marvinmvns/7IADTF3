"""Configuração do banco de dados PostgreSQL com SQLAlchemy async."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

logger = logging.getLogger("medassist")
settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migrações incrementais: adiciona colunas novas se não existirem
    migrations = [
        ("pacientes", "cep", "VARCHAR(10)"),
        ("pacientes", "endereco", "VARCHAR(500)"),
        ("pacientes", "bairro", "VARCHAR(200)"),
        ("pacientes", "cidade", "VARCHAR(200)"),
        ("pacientes", "estado", "VARCHAR(2)"),
        ("triagens", "nivel_urgencia", "INTEGER"),
        ("triagens", "diagnosticos_possiveis", "TEXT"),
    ]
    async with engine.begin() as conn:
        for table, col, typ in migrations:
            await conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
            logger.info(f"Migração: coluna {table}.{col} verificada")
