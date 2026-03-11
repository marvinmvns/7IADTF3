"""Controller de Triagem - rotas REST com classificação de risco."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import TriagemCreate, TriagemOut
from app.services.triagem_service import TriagemService
from app.services.llm.langchain_service import LangChainService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/triagens", tags=["Triagem"])


@router.post("/", response_model=TriagemOut)
async def criar_triagem(dados: TriagemCreate, db: AsyncSession = Depends(get_db)):
    llm = LangChainService(db)
    orientacao = await llm.orientar_triagem(dados.sintomas)
    triagem = await TriagemService.criar(db, dados, orientacao)
    await registrar_log(
        db, "triagem_criada",
        f"Triagem #{triagem.id} - Risco: {triagem.classificacao_risco}"
    )
    return triagem


@router.get("/paciente/{paciente_id}", response_model=list[TriagemOut])
async def listar_triagens(paciente_id: int, db: AsyncSession = Depends(get_db)):
    return await TriagemService.listar_por_paciente(db, paciente_id)
