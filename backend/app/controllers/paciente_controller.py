"""Controller de Paciente - rotas REST."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import PacienteCreate, PacienteOut, FichaPacienteOut
from app.services.paciente_service import PacienteService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


@router.post("/", response_model=PacienteOut)
async def criar_paciente(dados: PacienteCreate, db: AsyncSession = Depends(get_db)):
    existente = await PacienteService.buscar_por_cpf(db, dados.cpf)
    if existente:
        raise HTTPException(400, "CPF já cadastrado")
    paciente = await PacienteService.criar(db, dados)
    await registrar_log(db, "paciente_criado", f"Paciente {dados.nome} cadastrado")
    return paciente


@router.get("/cpf/{cpf}", response_model=PacienteOut)
async def buscar_por_cpf(cpf: str, db: AsyncSession = Depends(get_db)):
    paciente = await PacienteService.buscar_por_cpf(db, cpf)
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado")
    return paciente


@router.get("/cpf/{cpf}/ficha", response_model=FichaPacienteOut)
async def ficha_completa(cpf: str, db: AsyncSession = Depends(get_db)):
    paciente = await PacienteService.ficha_completa(db, cpf)
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado")
    return FichaPacienteOut(
        paciente=paciente,
        prontuarios=paciente.prontuarios,
        triagens=paciente.triagens,
        conversas=paciente.conversas,
    )


@router.get("/", response_model=list[PacienteOut])
async def listar_pacientes(skip: int = 0, limit: int = 50,
                           db: AsyncSession = Depends(get_db)):
    return await PacienteService.listar(db, skip, limit)
