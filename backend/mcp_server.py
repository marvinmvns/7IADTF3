"""
MCP Server - MedAssist
Expõe ferramentas para acessar dados de pacientes, prontuários e triagens
via Model Context Protocol (SSE transport).

Uso: python mcp_server.py
Acesse via: http://localhost:8090/sse
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import Base
from app.models import Paciente, Prontuario, Triagem, Conversa, Mensagem, LogAuditoria

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-medassist")

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
SessionMCP = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_datetime(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


def _fmt_cpf(cpf_raw: str) -> str:
    cpf = re.sub(r"\D", "", cpf_raw)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf_raw


def _paciente_to_dict(p: Paciente) -> dict:
    return {
        "id": p.id,
        "cpf": p.cpf,
        "nome": p.nome,
        "data_nascimento": p.data_nascimento,
        "sexo": p.sexo,
        "telefone": p.telefone,
        "email": p.email,
        "cep": p.cep,
        "endereco": p.endereco,
        "bairro": p.bairro,
        "cidade": p.cidade,
        "estado": p.estado,
        "criado_em": _fmt_datetime(p.criado_em),
    }


def _prontuario_to_dict(pr: Prontuario) -> dict:
    return {
        "id": pr.id,
        "diagnostico": pr.diagnostico,
        "medicamentos": pr.medicamentos,
        "alergias": pr.alergias,
        "observacoes": pr.observacoes,
        "medico_responsavel": pr.medico_responsavel,
        "data_consulta": _fmt_datetime(pr.data_consulta),
        "criado_em": _fmt_datetime(pr.criado_em),
    }


def _triagem_to_dict(t: Triagem) -> dict:
    return {
        "id": t.id,
        "sintomas": t.sintomas,
        "classificacao_risco": t.classificacao_risco,
        "pressao_arterial": t.pressao_arterial,
        "temperatura": t.temperatura,
        "frequencia_cardiaca": t.frequencia_cardiaca,
        "saturacao": t.saturacao,
        "orientacao_ia": t.orientacao_ia,
        "nivel_urgencia": t.nivel_urgencia,
        "diagnosticos_possiveis": t.diagnosticos_possiveis,
        "validado_por_humano": t.validado_por_humano,
        "criado_em": _fmt_datetime(t.criado_em),
    }


def _conversa_to_dict(c: Conversa) -> dict:
    msgs = []
    if hasattr(c, "mensagens") and c.mensagens:
        for m in c.mensagens:
            msgs.append({
                "papel": m.papel,
                "conteudo": m.conteudo,
                "fonte": m.fonte,
                "criado_em": _fmt_datetime(m.criado_em),
            })
    return {
        "id": c.id,
        "tipo": c.tipo,
        "criado_em": _fmt_datetime(c.criado_em),
        "mensagens": msgs,
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = Server("medassist-mcp")


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="buscar_paciente_cpf",
            description=(
                "Busca um paciente pelo CPF e retorna seus dados cadastrais. "
                "Aceita CPF com ou sem formatação (ex: 12345678900 ou 123.456.789-00)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente (com ou sem formatação)",
                    }
                },
                "required": ["cpf"],
            },
        ),
        Tool(
            name="ficha_completa_paciente",
            description=(
                "Retorna a ficha completa do paciente: dados cadastrais, todos os "
                "prontuários médicos, triagens realizadas e histórico de conversas. "
                "Aceita CPF com ou sem formatação."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente",
                    }
                },
                "required": ["cpf"],
            },
        ),
        Tool(
            name="listar_pacientes",
            description=(
                "Lista todos os pacientes cadastrados no sistema. "
                "Retorna nome, CPF e dados de contato."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de pacientes (padrão: 50)",
                        "default": 50,
                    }
                },
            },
        ),
        Tool(
            name="prontuarios_paciente",
            description=(
                "Retorna todos os prontuários médicos de um paciente pelo CPF. "
                "Inclui diagnósticos, medicamentos, alergias e observações."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente",
                    }
                },
                "required": ["cpf"],
            },
        ),
        Tool(
            name="triagens_paciente",
            description=(
                "Retorna todas as triagens de um paciente pelo CPF. "
                "Inclui classificação de risco (Manchester), sinais vitais e orientação da IA."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente",
                    }
                },
                "required": ["cpf"],
            },
        ),
        Tool(
            name="historico_conversas_paciente",
            description=(
                "Retorna o histórico de conversas (chat) de um paciente pelo CPF. "
                "Inclui tipo da conversa e todas as mensagens trocadas."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente",
                    }
                },
                "required": ["cpf"],
            },
        ),
        Tool(
            name="buscar_paciente_nome",
            description=(
                "Busca pacientes pelo nome (busca parcial, case-insensitive). "
                "Retorna dados cadastrais dos pacientes encontrados."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome ou parte do nome do paciente",
                    }
                },
                "required": ["nome"],
            },
        ),
        Tool(
            name="resumo_atendimento",
            description=(
                "Gera um resumo estruturado para atendimento de um paciente. "
                "Inclui dados pessoais, última triagem, último prontuário, alergias "
                "conhecidas e medicamentos em uso. Ideal para preparar o profissional "
                "de saúde antes do atendimento."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cpf": {
                        "type": "string",
                        "description": "CPF do paciente",
                    }
                },
                "required": ["cpf"],
            },
        ),
    ]


async def _get_paciente_by_cpf(cpf: str) -> Paciente | None:
    cpf_fmt = _fmt_cpf(cpf)
    async with SessionMCP() as db:
        stmt = select(Paciente).where(Paciente.cpf == cpf_fmt)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


async def _get_ficha_completa(cpf: str):
    cpf_fmt = _fmt_cpf(cpf)
    async with SessionMCP() as db:
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


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "buscar_paciente_cpf":
            paciente = await _get_paciente_by_cpf(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]
            return [TextContent(type="text", text=json.dumps(_paciente_to_dict(paciente), ensure_ascii=False, indent=2))]

        elif name == "ficha_completa_paciente":
            paciente = await _get_ficha_completa(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]
            ficha = {
                "paciente": _paciente_to_dict(paciente),
                "prontuarios": [_prontuario_to_dict(pr) for pr in paciente.prontuarios],
                "triagens": [_triagem_to_dict(t) for t in paciente.triagens],
                "conversas": [_conversa_to_dict(c) for c in paciente.conversas],
            }
            return [TextContent(type="text", text=json.dumps(ficha, ensure_ascii=False, indent=2))]

        elif name == "listar_pacientes":
            limite = arguments.get("limite", 50)
            async with SessionMCP() as db:
                stmt = select(Paciente).limit(limite)
                result = await db.execute(stmt)
                pacientes = result.scalars().all()
            lista = [_paciente_to_dict(p) for p in pacientes]
            if not lista:
                return [TextContent(type="text", text="Nenhum paciente cadastrado no sistema.")]
            return [TextContent(type="text", text=json.dumps(lista, ensure_ascii=False, indent=2))]

        elif name == "prontuarios_paciente":
            paciente = await _get_ficha_completa(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]
            prontuarios = [_prontuario_to_dict(pr) for pr in paciente.prontuarios]
            if not prontuarios:
                return [TextContent(type="text", text=f"Paciente {paciente.nome} não possui prontuários registrados.")]
            result = {
                "paciente": paciente.nome,
                "cpf": paciente.cpf,
                "prontuarios": prontuarios,
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "triagens_paciente":
            paciente = await _get_ficha_completa(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]
            triagens = [_triagem_to_dict(t) for t in paciente.triagens]
            if not triagens:
                return [TextContent(type="text", text=f"Paciente {paciente.nome} não possui triagens registradas.")]
            result = {
                "paciente": paciente.nome,
                "cpf": paciente.cpf,
                "triagens": triagens,
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "historico_conversas_paciente":
            paciente = await _get_ficha_completa(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]
            conversas = [_conversa_to_dict(c) for c in paciente.conversas]
            if not conversas:
                return [TextContent(type="text", text=f"Paciente {paciente.nome} não possui conversas registradas.")]
            result = {
                "paciente": paciente.nome,
                "cpf": paciente.cpf,
                "conversas": conversas,
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "buscar_paciente_nome":
            nome = arguments["nome"]
            async with SessionMCP() as db:
                stmt = select(Paciente).where(Paciente.nome.ilike(f"%{nome}%")).limit(20)
                result = await db.execute(stmt)
                pacientes = result.scalars().all()
            if not pacientes:
                return [TextContent(type="text", text=f"Nenhum paciente encontrado com o nome '{nome}'.")]
            lista = [_paciente_to_dict(p) for p in pacientes]
            return [TextContent(type="text", text=json.dumps(lista, ensure_ascii=False, indent=2))]

        elif name == "resumo_atendimento":
            paciente = await _get_ficha_completa(arguments["cpf"])
            if not paciente:
                return [TextContent(type="text", text="Paciente não encontrado para o CPF informado.")]

            # Última triagem
            ultima_triagem = None
            if paciente.triagens:
                ultima = sorted(paciente.triagens, key=lambda t: t.criado_em or datetime.min, reverse=True)[0]
                ultima_triagem = _triagem_to_dict(ultima)

            # Último prontuário
            ultimo_prontuario = None
            alergias_conhecidas = []
            medicamentos_uso = []
            if paciente.prontuarios:
                for pr in paciente.prontuarios:
                    if pr.alergias:
                        alergias_conhecidas.append(pr.alergias)
                    if pr.medicamentos:
                        medicamentos_uso.append(pr.medicamentos)
                ultimo = sorted(paciente.prontuarios, key=lambda p: p.criado_em or datetime.min, reverse=True)[0]
                ultimo_prontuario = _prontuario_to_dict(ultimo)

            resumo = {
                "paciente": _paciente_to_dict(paciente),
                "total_prontuarios": len(paciente.prontuarios),
                "total_triagens": len(paciente.triagens),
                "total_conversas": len(paciente.conversas),
                "ultima_triagem": ultima_triagem,
                "ultimo_prontuario": ultimo_prontuario,
                "alergias_conhecidas": list(set(alergias_conhecidas)),
                "medicamentos_em_uso": list(set(medicamentos_uso)),
            }
            return [TextContent(type="text", text=json.dumps(resumo, ensure_ascii=False, indent=2))]

        else:
            return [TextContent(type="text", text=f"Ferramenta '{name}' não reconhecida.")]

    except Exception as e:
        logger.error(f"Erro ao executar ferramenta {name}: {e}")
        return [TextContent(type="text", text=f"Erro ao executar: {str(e)}")]


# ---------------------------------------------------------------------------
# SSE Transport via Starlette
# ---------------------------------------------------------------------------

sse = SseServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(
            streams[0], streams[1], mcp.create_initialization_options()
        )


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ],
)

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando MCP Server MedAssist na porta 8091...")
    logger.info("SSE endpoint: http://localhost:8091/sse")
    uvicorn.run(app, host="0.0.0.0", port=8091)
