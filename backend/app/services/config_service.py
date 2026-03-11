"""Service de configuração de LLM e parâmetros."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ConfigLLM
from app.schemas.schemas import ConfigLLMUpdate


class ConfigService:

    @staticmethod
    async def obter_ativa(db: AsyncSession) -> ConfigLLM | None:
        stmt = select(ConfigLLM).where(ConfigLLM.ativo == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def salvar(db: AsyncSession, dados: ConfigLLMUpdate) -> ConfigLLM:
        # Desativa todas as configs anteriores
        stmt = select(ConfigLLM).where(ConfigLLM.ativo == True)
        result = await db.execute(stmt)
        for cfg in result.scalars().all():
            cfg.ativo = False

        config = ConfigLLM(**dados.model_dump(), ativo=True)
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def listar(db: AsyncSession):
        stmt = select(ConfigLLM).order_by(ConfigLLM.atualizado_em.desc())
        result = await db.execute(stmt)
        return result.scalars().all()
