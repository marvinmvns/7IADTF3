"""Controller de Triagem - rotas REST com classificação de risco."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Triagem
from app.schemas.schemas import TriagemCreate, TriagemOut
from app.services.triagem_service import TriagemService
from app.services.llm.langchain_service import LangChainService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/triagens", tags=["Triagem"])


@router.post("/", response_model=TriagemOut)
async def criar_triagem(dados: TriagemCreate, db: AsyncSession = Depends(get_db)):
    orientacao = ""
    try:
        llm = LangChainService(db)
        orientacao = await llm.orientar_triagem(dados.sintomas)
    except Exception:
        pass  # LLM indisponível — LangGraph ainda gera orientação
    triagem = await TriagemService.criar(db, dados, orientacao)
    await registrar_log(
        db, "triagem_criada",
        f"Triagem #{triagem.id} - Risco: {triagem.classificacao_risco} - "
        f"Paciente: {triagem.paciente_id} - Orientação: {triagem.orientacao_ia}"
    )
    return triagem


@router.patch("/{triagem_id}/validar", response_model=TriagemOut)
async def validar_triagem(triagem_id: int, db: AsyncSession = Depends(get_db)):
    """Valida uma triagem por um profissional humano."""
    result = await db.execute(
        select(Triagem).where(Triagem.id == triagem_id)
    )
    triagem = result.scalar_one_or_none()
    if not triagem:
        raise HTTPException(404, "Triagem não encontrada.")
    triagem.validado_por_humano = True
    await db.commit()
    await db.refresh(triagem)
    await registrar_log(
        db, "triagem_validada",
        f"Triagem #{triagem.id} validada por humano - Risco: {triagem.classificacao_risco}"
    )
    return triagem


@router.get("/paciente/{paciente_id}", response_model=list[TriagemOut])
async def listar_triagens(paciente_id: int, db: AsyncSession = Depends(get_db)):
    return await TriagemService.listar_por_paciente(db, paciente_id)
