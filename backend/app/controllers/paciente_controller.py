"""Controller de Paciente - rotas REST."""
import re
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
    await registrar_log(db, "paciente_consulta", f"Consulta por CPF: {cpf}")
    return paciente


@router.get("/cpf/{cpf}/ficha", response_model=FichaPacienteOut)
async def ficha_completa(cpf: str, db: AsyncSession = Depends(get_db)):
    paciente = await PacienteService.ficha_completa(db, cpf)
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado")
    await registrar_log(db, "paciente_ficha_acessada", f"Ficha completa acessada - CPF: {cpf}")
    return FichaPacienteOut(
        paciente=paciente,
        prontuarios=paciente.prontuarios,
        triagens=paciente.triagens,
        conversas=paciente.conversas,
    )


@router.get("/cep-lookup/{cep}")
async def buscar_cep(cep: str):
    import httpx
    cep_limpo = re.sub(r"\D", "", cep)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"https://viacep.com.br/ws/{cep_limpo}/json/")
        data = resp.json()
        if "erro" in data:
            raise HTTPException(404, "CEP não encontrado")
        return {
            "cep": data.get("cep", ""),
            "endereco": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "estado": data.get("uf", ""),
        }


@router.put("/{paciente_id}", response_model=PacienteOut)
async def atualizar_paciente(paciente_id: int, dados: PacienteCreate,
                             db: AsyncSession = Depends(get_db)):
    paciente = await PacienteService.atualizar(db, paciente_id, dados.model_dump())
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado")
    await registrar_log(db, "paciente_atualizado", f"Paciente #{paciente_id} atualizado")
    return paciente


@router.delete("/{paciente_id}")
async def remover_paciente(paciente_id: int, db: AsyncSession = Depends(get_db)):
    removido = await PacienteService.remover(db, paciente_id)
    if not removido:
        raise HTTPException(404, "Paciente não encontrado")
    await registrar_log(db, "paciente_removido", f"Paciente #{paciente_id} removido")
    return {"status": "removido"}


@router.get("/", response_model=list[PacienteOut])
async def listar_pacientes(skip: int = 0, limit: int = 50,
                           db: AsyncSession = Depends(get_db)):
    return await PacienteService.listar(db, skip, limit)
