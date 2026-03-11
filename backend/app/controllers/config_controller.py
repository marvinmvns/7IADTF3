"""Controller de Configuração - parametrização de LLM e TTS."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import ConfigLLMUpdate, ConfigLLMOut
from app.services.config_service import ConfigService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/config", tags=["Configuração"])


@router.get("/llm", response_model=ConfigLLMOut | None)
async def obter_config(db: AsyncSession = Depends(get_db)):
    return await ConfigService.obter_ativa(db)


@router.post("/llm", response_model=ConfigLLMOut)
async def salvar_config(dados: ConfigLLMUpdate, db: AsyncSession = Depends(get_db)):
    config = await ConfigService.salvar(db, dados)
    await registrar_log(db, "config_atualizada", f"Provider: {dados.provider}, Model: {dados.model_name}")
    return config


@router.get("/llm/historico", response_model=list[ConfigLLMOut])
async def historico_configs(db: AsyncSession = Depends(get_db)):
    return await ConfigService.listar(db)
