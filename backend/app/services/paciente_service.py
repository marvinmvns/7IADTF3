"""Service para operações de Paciente e Prontuário."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Paciente, Prontuario, Triagem, Conversa
from app.schemas.schemas import PacienteCreate, ProntuarioCreate
import re


class PacienteService:

    @staticmethod
    async def buscar_por_cpf(db: AsyncSession, cpf: str) -> Paciente | None:
        cpf_limpo = re.sub(r"\D", "", cpf)
        cpf_fmt = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        stmt = select(Paciente).where(Paciente.cpf == cpf_fmt)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def ficha_completa(db: AsyncSession, cpf: str):
        cpf_limpo = re.sub(r"\D", "", cpf)
        cpf_fmt = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        stmt = (
            select(Paciente)
            .options(
                selectinload(Paciente.prontuarios),
                selectinload(Paciente.triagens),
                selectinload(Paciente.conversas).selectinload(Conversa.mensagens),
            )
            .where(Paciente.cpf == cpf_fmt)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def criar(db: AsyncSession, dados: PacienteCreate) -> Paciente:
        paciente = Paciente(**dados.model_dump())
        db.add(paciente)
        await db.commit()
        await db.refresh(paciente)
        return paciente

    @staticmethod
    async def listar(db: AsyncSession, skip: int = 0, limit: int = 50):
        stmt = select(Paciente).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()


class ProntuarioService:

    @staticmethod
    async def criar(db: AsyncSession, dados: ProntuarioCreate) -> Prontuario:
        prontuario = Prontuario(**dados.model_dump())
        db.add(prontuario)
        await db.commit()
        await db.refresh(prontuario)
        return prontuario

    @staticmethod
    async def listar_por_paciente(db: AsyncSession, paciente_id: int):
        stmt = select(Prontuario).where(Prontuario.paciente_id == paciente_id)
        result = await db.execute(stmt)
        return result.scalars().all()
