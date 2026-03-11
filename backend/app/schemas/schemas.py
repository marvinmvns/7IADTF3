"""Schemas Pydantic para validação de entrada/saída."""
from pydantic import BaseModel, field_validator
from datetime import datetime
import re


# --- Paciente ---
class PacienteCreate(BaseModel):
    cpf: str
    nome: str
    data_nascimento: str
    sexo: str
    telefone: str | None = None
    email: str | None = None

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        cpf = re.sub(r"\D", "", v)
        if len(cpf) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    @field_validator("sexo")
    @classmethod
    def validar_sexo(cls, v: str) -> str:
        if v.upper() not in ("M", "F"):
            raise ValueError("Sexo deve ser M ou F")
        return v.upper()


class PacienteOut(BaseModel):
    id: int
    cpf: str
    nome: str
    data_nascimento: str
    sexo: str
    telefone: str | None
    email: str | None
    criado_em: datetime

    class Config:
        from_attributes = True


# --- Prontuário ---
class ProntuarioCreate(BaseModel):
    paciente_id: int
    diagnostico: str
    medicamentos: str | None = None
    alergias: str | None = None
    observacoes: str | None = None
    medico_responsavel: str


class ProntuarioOut(BaseModel):
    id: int
    paciente_id: int
    diagnostico: str
    medicamentos: str | None
    alergias: str | None
    observacoes: str | None
    medico_responsavel: str
    data_consulta: datetime
    criado_em: datetime

    class Config:
        from_attributes = True


# --- Triagem ---
class TriagemCreate(BaseModel):
    paciente_id: int
    sintomas: str
    pressao_arterial: str | None = None
    temperatura: float | None = None
    frequencia_cardiaca: int | None = None
    saturacao: int | None = None


class TriagemOut(BaseModel):
    id: int
    paciente_id: int
    sintomas: str
    classificacao_risco: str
    pressao_arterial: str | None
    temperatura: float | None
    frequencia_cardiaca: int | None
    saturacao: int | None
    orientacao_ia: str | None
    validado_por_humano: bool
    criado_em: datetime

    class Config:
        from_attributes = True


# --- Chat ---
class MensagemIn(BaseModel):
    conteudo: str
    conversa_id: int | None = None
    paciente_id: int | None = None
    tipo: str = "geral"  # triagem | consulta | geral


class MensagemOut(BaseModel):
    id: int
    conversa_id: int
    papel: str
    conteudo: str
    fonte: str | None
    criado_em: datetime

    class Config:
        from_attributes = True


class ConversaOut(BaseModel):
    id: int
    paciente_id: int | None
    tipo: str
    criado_em: datetime
    mensagens: list[MensagemOut] = []

    class Config:
        from_attributes = True


# --- Config LLM ---
class ConfigLLMUpdate(BaseModel):
    provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    tts_engine: str = "piper"
    stt_engine: str = "vosk"


class ConfigLLMOut(BaseModel):
    id: int
    provider: str
    model_name: str
    base_url: str | None
    temperature: float
    max_tokens: int
    tts_engine: str
    stt_engine: str
    ativo: bool
    atualizado_em: datetime

    class Config:
        from_attributes = True


# --- Scraping ---
class ScrapingRequest(BaseModel):
    fonte: str  # pubmed | medlineplus | bvs | datasus | mayo | drauzio
    termo: str
    max_resultados: int = 10


class DadoMedicoOut(BaseModel):
    id: int
    fonte: str
    titulo: str
    conteudo: str
    url: str
    categoria: str | None
    coletado_em: datetime

    class Config:
        from_attributes = True


# --- Ficha Completa ---
class FichaPacienteOut(BaseModel):
    paciente: PacienteOut
    prontuarios: list[ProntuarioOut] = []
    triagens: list[TriagemOut] = []
    conversas: list[ConversaOut] = []
