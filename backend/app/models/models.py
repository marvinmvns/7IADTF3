"""Models do banco de dados - Entidades principais."""
from datetime import datetime
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
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    data_consulta: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    validado_por_humano: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    paciente: Mapped["Paciente"] = relationship(back_populates="triagens")


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))  # triagem | consulta | geral
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    paciente: Mapped["Paciente"] = relationship(back_populates="conversas")
    mensagens: Mapped[list["Mensagem"]] = relationship(back_populates="conversa")


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"))
    papel: Mapped[str] = mapped_column(String(20))  # user | assistant | system
    conteudo: Mapped[str] = mapped_column(Text)
    fonte: Mapped[str] = mapped_column(Text, nullable=True)  # explainability
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DadoMedico(Base):
    __tablename__ = "dados_medicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fonte: Mapped[str] = mapped_column(String(200))  # pubmed, medlineplus, bvs, etc
    titulo: Mapped[str] = mapped_column(String(500))
    conteudo: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000))
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)
    metadata_extra: Mapped[dict] = mapped_column(JSON, nullable=True)
    coletado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    acao: Mapped[str] = mapped_column(String(100))
    detalhes: Mapped[str] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(200), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
