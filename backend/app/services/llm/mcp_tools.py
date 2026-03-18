"""Tools LangChain para acesso a dados de pacientes via banco de dados.

Estas ferramentas são disponibilizadas ao LLM para que ele possa buscar
dados de pacientes, prontuários, triagens e conversas automaticamente
durante o chat.
"""
import json
import re
import logging
from datetime import datetime
from langchain.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from app.config import get_settings
from app.models import Paciente, Prontuario, Triagem, Conversa

logger = logging.getLogger("medassist.mcp_tools")

settings = get_settings()
_engine = create_async_engine(settings.database_url, echo=False)
_Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else ""


def _fmt_cpf(cpf_raw: str) -> str:
    cpf = re.sub(r"\D", "", cpf_raw)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf_raw


def _paciente_dict(p: Paciente) -> dict:
    return {
        "id": p.id, "cpf": p.cpf, "nome": p.nome,
        "data_nascimento": p.data_nascimento, "sexo": p.sexo,
        "telefone": p.telefone, "email": p.email,
        "cep": p.cep, "endereco": p.endereco,
        "bairro": p.bairro, "cidade": p.cidade, "estado": p.estado,
        "criado_em": _fmt_dt(p.criado_em),
    }


def _prontuario_dict(pr: Prontuario) -> dict:
    return {
        "id": pr.id, "diagnostico": pr.diagnostico,
        "medicamentos": pr.medicamentos, "alergias": pr.alergias,
        "observacoes": pr.observacoes, "medico_responsavel": pr.medico_responsavel,
        "data_consulta": _fmt_dt(pr.data_consulta),
    }


def _triagem_dict(t: Triagem) -> dict:
    return {
        "id": t.id, "sintomas": t.sintomas,
        "classificacao_risco": t.classificacao_risco,
        "pressao_arterial": t.pressao_arterial,
        "temperatura": t.temperatura, "frequencia_cardiaca": t.frequencia_cardiaca,
        "saturacao": t.saturacao, "orientacao_ia": t.orientacao_ia,
        "nivel_urgencia": t.nivel_urgencia,
        "diagnosticos_possiveis": t.diagnosticos_possiveis,
        "validado_por_humano": t.validado_por_humano,
        "criado_em": _fmt_dt(t.criado_em),
    }


async def _buscar_paciente(cpf: str) -> Paciente | None:
    cpf_fmt = _fmt_cpf(cpf)
    async with _Session() as db:
        stmt = select(Paciente).where(Paciente.cpf == cpf_fmt)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


async def _ficha_completa(cpf: str):
    cpf_fmt = _fmt_cpf(cpf)
    async with _Session() as db:
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


# ---------------------------------------------------------------------------
# LangChain Tools
# ---------------------------------------------------------------------------

@tool
async def buscar_paciente_cpf(cpf: str) -> str:
    """Busca um paciente pelo CPF e retorna seus dados cadastrais.
    Aceita CPF com ou sem formatação (ex: 12345678900 ou 123.456.789-00).
    Use esta ferramenta quando o usuário mencionar um CPF ou pedir dados de um paciente por CPF."""
    paciente = await _buscar_paciente(cpf)
    if not paciente:
        return "Paciente não encontrado para o CPF informado."
    return json.dumps(_paciente_dict(paciente), ensure_ascii=False, indent=2)


@tool
async def ficha_completa_paciente(cpf: str) -> str:
    """Retorna a ficha completa do paciente: dados cadastrais, prontuários médicos,
    triagens realizadas e histórico de conversas.
    Use quando o usuário pedir a ficha, histórico completo ou todos os dados de um paciente."""
    paciente = await _ficha_completa(cpf)
    if not paciente:
        return "Paciente não encontrado para o CPF informado."
    ficha = {
        "paciente": _paciente_dict(paciente),
        "prontuarios": [_prontuario_dict(pr) for pr in paciente.prontuarios],
        "triagens": [_triagem_dict(t) for t in paciente.triagens],
        "total_conversas": len(paciente.conversas),
    }
    return json.dumps(ficha, ensure_ascii=False, indent=2)


@tool
async def listar_pacientes(limite: int = 20) -> str:
    """Lista todos os pacientes cadastrados no sistema.
    Use quando o usuário pedir para ver os pacientes, listar pacientes ou quiser saber quem está cadastrado."""
    async with _Session() as db:
        stmt = select(Paciente).limit(limite)
        result = await db.execute(stmt)
        pacientes = result.scalars().all()
    if not pacientes:
        return "Nenhum paciente cadastrado no sistema."
    lista = [{"nome": p.nome, "cpf": p.cpf, "sexo": p.sexo, "telefone": p.telefone} for p in pacientes]
    return json.dumps(lista, ensure_ascii=False, indent=2)


@tool
async def prontuarios_paciente(cpf: str) -> str:
    """Retorna os prontuários médicos de um paciente pelo CPF.
    Inclui diagnósticos, medicamentos, alergias e observações.
    Use quando o usuário pedir prontuário, diagnóstico ou histórico médico de um paciente."""
    paciente = await _ficha_completa(cpf)
    if not paciente:
        return "Paciente não encontrado para o CPF informado."
    if not paciente.prontuarios:
        return f"Paciente {paciente.nome} não possui prontuários registrados."
    result = {
        "paciente": paciente.nome,
        "cpf": paciente.cpf,
        "prontuarios": [_prontuario_dict(pr) for pr in paciente.prontuarios],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
async def triagens_paciente(cpf: str) -> str:
    """Retorna as triagens de um paciente pelo CPF.
    Inclui classificação de risco Manchester, sinais vitais e orientação da IA.
    Use quando o usuário pedir triagem, classificação de risco ou sinais vitais de um paciente."""
    paciente = await _ficha_completa(cpf)
    if not paciente:
        return "Paciente não encontrado para o CPF informado."
    if not paciente.triagens:
        return f"Paciente {paciente.nome} não possui triagens registradas."
    result = {
        "paciente": paciente.nome,
        "cpf": paciente.cpf,
        "triagens": [_triagem_dict(t) for t in paciente.triagens],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
async def buscar_paciente_nome(nome: str) -> str:
    """Busca pacientes pelo nome (busca parcial, não precisa ser exato).
    Use quando o usuário mencionar o nome de um paciente sem fornecer CPF."""
    async with _Session() as db:
        stmt = select(Paciente).where(Paciente.nome.ilike(f"%{nome}%")).limit(10)
        result = await db.execute(stmt)
        pacientes = result.scalars().all()
    if not pacientes:
        return f"Nenhum paciente encontrado com o nome '{nome}'."
    lista = [_paciente_dict(p) for p in pacientes]
    return json.dumps(lista, ensure_ascii=False, indent=2)


@tool
async def resumo_atendimento(cpf: str) -> str:
    """Gera um resumo estruturado para atendimento de um paciente.
    Inclui dados pessoais, última triagem, último prontuário, alergias e medicamentos em uso.
    Use quando o usuário pedir um resumo para atendimento ou preparação para consulta."""
    paciente = await _ficha_completa(cpf)
    if not paciente:
        return "Paciente não encontrado para o CPF informado."

    ultima_triagem = None
    if paciente.triagens:
        ultima = sorted(paciente.triagens, key=lambda t: t.criado_em or datetime.min, reverse=True)[0]
        ultima_triagem = _triagem_dict(ultima)

    ultimo_prontuario = None
    alergias = set()
    medicamentos = set()
    if paciente.prontuarios:
        for pr in paciente.prontuarios:
            if pr.alergias:
                alergias.add(pr.alergias)
            if pr.medicamentos:
                medicamentos.add(pr.medicamentos)
        ultimo = sorted(paciente.prontuarios, key=lambda p: p.criado_em or datetime.min, reverse=True)[0]
        ultimo_prontuario = _prontuario_dict(ultimo)

    resumo = {
        "paciente": _paciente_dict(paciente),
        "total_prontuarios": len(paciente.prontuarios),
        "total_triagens": len(paciente.triagens),
        "ultima_triagem": ultima_triagem,
        "ultimo_prontuario": ultimo_prontuario,
        "alergias_conhecidas": list(alergias),
        "medicamentos_em_uso": list(medicamentos),
    }
    return json.dumps(resumo, ensure_ascii=False, indent=2)


# Lista de todas as ferramentas para uso no LangChain agent
ALL_TOOLS = [
    buscar_paciente_cpf,
    ficha_completa_paciente,
    listar_pacientes,
    prontuarios_paciente,
    triagens_paciente,
    buscar_paciente_nome,
    resumo_atendimento,
]
