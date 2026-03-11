"""Controller de Prontuário - rotas REST."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import ProntuarioCreate, ProntuarioOut
from app.services.paciente_service import ProntuarioService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/prontuarios", tags=["Prontuários"])


@router.post("/", response_model=ProntuarioOut)
async def criar_prontuario(dados: ProntuarioCreate, db: AsyncSession = Depends(get_db)):
    prontuario = await ProntuarioService.criar(db, dados)
    await registrar_log(db, "prontuario_criado", f"Prontuário #{prontuario.id} criado")
    return prontuario


@router.get("/paciente/{paciente_id}", response_model=list[ProntuarioOut])
async def listar_prontuarios(paciente_id: int, db: AsyncSession = Depends(get_db)):
    return await ProntuarioService.listar_por_paciente(db, paciente_id)
