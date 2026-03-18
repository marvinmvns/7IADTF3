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

    @staticmethod
    async def atualizar(db: AsyncSession, paciente_id: int, dados: dict) -> Paciente | None:
        stmt = select(Paciente).where(Paciente.id == paciente_id)
        result = await db.execute(stmt)
        paciente = result.scalar_one_or_none()
        if not paciente:
            return None
        for key, value in dados.items():
            if value is not None and hasattr(paciente, key):
                setattr(paciente, key, value)
        await db.commit()
        await db.refresh(paciente)
        return paciente

    @staticmethod
    async def remover(db: AsyncSession, paciente_id: int) -> bool:
        from sqlalchemy import delete as sql_delete
        from app.models.models import Mensagem

        stmt = select(Paciente).where(Paciente.id == paciente_id)
        result = await db.execute(stmt)
        paciente = result.scalar_one_or_none()
        if not paciente:
            return False

        # Remove dados relacionados (cascade manual)
        # 1. Mensagens das conversas do paciente
        conversas = await db.execute(
            select(Conversa).where(Conversa.paciente_id == paciente_id)
        )
        for conv in conversas.scalars().all():
            await db.execute(sql_delete(Mensagem).where(Mensagem.conversa_id == conv.id))

        # 2. Conversas, triagens, prontuários
        await db.execute(sql_delete(Conversa).where(Conversa.paciente_id == paciente_id))
        await db.execute(sql_delete(Triagem).where(Triagem.paciente_id == paciente_id))
        await db.execute(sql_delete(Prontuario).where(Prontuario.paciente_id == paciente_id))

        # 3. Paciente
        await db.delete(paciente)
        await db.commit()
        return True


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
