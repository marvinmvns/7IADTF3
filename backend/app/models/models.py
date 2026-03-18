"""Models do banco de dados - Entidades principais."""
from datetime import datetime, timezone, timedelta

_BRT = timezone(timedelta(hours=-3))


def _now_brt():
    """Retorna datetime naive no fuso BRT (GMT-3) para colunas TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(_BRT).replace(tzinfo=None)
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cpf: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    data_nascimento: Mapped[str] = mapped_column(String(10))
    sexo: Mapped[str] = mapped_column(String(1))
    telefone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    cep: Mapped[str] = mapped_column(String(10), nullable=True)
    endereco: Mapped[str] = mapped_column(String(500), nullable=True)
    bairro: Mapped[str] = mapped_column(String(200), nullable=True)
    cidade: Mapped[str] = mapped_column(String(200), nullable=True)
    estado: Mapped[str] = mapped_column(String(2), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)

    prontuarios: Mapped[list["Prontuario"]] = relationship(back_populates="paciente")
    triagens: Mapped[list["Triagem"]] = relationship(back_populates="paciente")
    conversas: Mapped[list["Conversa"]] = relationship(back_populates="paciente")


class Prontuario(Base):
    __tablename__ = "prontuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"))
    diagnostico: Mapped[str] = mapped_column(Text)
    medicamentos: Mapped[str] = mapped_column(Text, nullable=True)
    alergias: Mapped[str] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, nullable=True)
    medico_responsavel: Mapped[str] = mapped_column(String(200))
    data_consulta: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)

    paciente: Mapped["Paciente"] = relationship(back_populates="prontuarios")


class Triagem(Base):
    __tablename__ = "triagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"))
    sintomas: Mapped[str] = mapped_column(Text)
    classificacao_risco: Mapped[str] = mapped_column(String(20))  # vermelho, laranja, amarelo, verde, azul
    pressao_arterial: Mapped[str] = mapped_column(String(20), nullable=True)
    temperatura: Mapped[float] = mapped_column(Float, nullable=True)
    frequencia_cardiaca: Mapped[int] = mapped_column(Integer, nullable=True)
    saturacao: Mapped[int] = mapped_column(Integer, nullable=True)
    orientacao_ia: Mapped[str] = mapped_column(Text, nullable=True)
    nivel_urgencia: Mapped[int] = mapped_column(Integer, nullable=True)
    diagnosticos_possiveis: Mapped[str] = mapped_column(Text, nullable=True)
    validado_por_humano: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)

    paciente: Mapped["Paciente"] = relationship(back_populates="triagens")


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))  # triagem | consulta | geral
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)

    paciente: Mapped["Paciente"] = relationship(back_populates="conversas")
    mensagens: Mapped[list["Mensagem"]] = relationship(back_populates="conversa")


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"))
    papel: Mapped[str] = mapped_column(String(20))  # user | assistant | system
    conteudo: Mapped[str] = mapped_column(Text)
    fonte: Mapped[str] = mapped_column(Text, nullable=True)  # explainability
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)

    conversa: Mapped["Conversa"] = relationship(back_populates="mensagens")


class ConfigLLM(Base):
    __tablename__ = "config_llm"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))  # openai | ollama
    model_name: Mapped[str] = mapped_column(String(100))
    api_key: Mapped[str] = mapped_column(String(500), nullable=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    tts_engine: Mapped[str] = mapped_column(String(50), default="piper")
    stt_engine: Mapped[str] = mapped_column(String(50), default="vosk")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)


class DadoMedico(Base):
    __tablename__ = "dados_medicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fonte: Mapped[str] = mapped_column(String(200))  # pubmed, medlineplus, bvs, etc
    titulo: Mapped[str] = mapped_column(String(500))
    conteudo: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000))
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)
    metadata_extra: Mapped[dict] = mapped_column(JSON, nullable=True)
    coletado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    acao: Mapped[str] = mapped_column(String(100))
    detalhes: Mapped[str] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(200), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)


class FineTuningJob(Base):
    __tablename__ = "finetuning_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    modelo_base: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente, treinando, concluido, erro
    progresso: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    epoca_atual: Mapped[int] = mapped_column(Integer, default=0)
    epocas_total: Mapped[int] = mapped_column(Integer, default=3)
    loss_atual: Mapped[float] = mapped_column(Float, nullable=True)
    learning_rate: Mapped[float] = mapped_column(Float, default=2e-4)
    lora_r: Mapped[int] = mapped_column(Integer, default=8)
    lora_alpha: Mapped[int] = mapped_column(Integer, default=16)
    batch_size: Mapped[int] = mapped_column(Integer, default=2)
    max_length: Mapped[int] = mapped_column(Integer, default=512)
    dataset_size: Mapped[int] = mapped_column(Integer, default=0)
    erro_msg: Mapped[str] = mapped_column(Text, nullable=True)
    caminho_modelo: Mapped[str] = mapped_column(String(500), nullable=True)
    logs: Mapped[str] = mapped_column(Text, nullable=True)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    concluido_em: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)


class DatasetEntry(Base):
    __tablename__ = "dataset_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    pergunta: Mapped[str] = mapped_column(Text)
    contexto: Mapped[str] = mapped_column(Text, nullable=True)
    resposta: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_now_brt)
