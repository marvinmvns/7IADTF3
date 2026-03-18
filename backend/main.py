"""MedAssist - Assistente Médico Virtual | Ponto de entrada FastAPI."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, SessionLocal
from app.controllers import (
    paciente_controller,
    prontuario_controller,
    triagem_controller,
    chat_controller,
    config_controller,
    scraping_controller,
    finetuning_controller,
)
from app.controllers import rag_controller
from app.controllers import auditoria_controller

logger = logging.getLogger("medassist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Seed automático: popula dados de exemplo se banco estiver vazio
    try:
        from sqlalchemy import select, func
        from app.models.models import Paciente
        async with SessionLocal() as db:
            count = await db.execute(select(func.count(Paciente.id)))
            if count.scalar() == 0:
                logger.info("Banco vazio, executando seed...")
                import subprocess
                subprocess.run(["python", "scripts/seed_db.py"], check=True)
                logger.info("Seed concluído")
    except Exception as e:
        logger.warning(f"Seed automático falhou (dados podem já existir): {e}")

    # Importa dataset sintético se não existir
    try:
        from app.models.models import DatasetEntry
        async with SessionLocal() as db:
            count = await db.execute(select(func.count(DatasetEntry.id)))
            if count.scalar() == 0:
                from app.services.finetuning_service import importar_dataset_json
                entries = await importar_dataset_json(db)
                logger.info(f"Dataset importado: {len(entries)} entradas")
    except Exception as e:
        logger.warning(f"Import dataset falhou: {e}")

    # Indexa dados existentes no RAG ao iniciar
    try:
        from app.services.rag.rag_service import indexar_tudo
        async with SessionLocal() as db:
            resultado = await indexar_tudo(db)
            logger.info(f"RAG inicializado: {resultado['total_documentos']} documentos indexados")
    except Exception as e:
        logger.warning(f"RAG: indexação inicial falhou (será feita sob demanda): {e}")
    yield


app = FastAPI(
    title="MedAssist - Assistente Médico Virtual",
    description="API do assistente médico com triagem, chat IA, scraping, RAG e TTS/STT",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra controllers (rotas)
app.include_router(paciente_controller.router, prefix="/api")
app.include_router(prontuario_controller.router, prefix="/api")
app.include_router(triagem_controller.router, prefix="/api")
app.include_router(chat_controller.router, prefix="/api")
app.include_router(config_controller.router, prefix="/api")
app.include_router(scraping_controller.router, prefix="/api")
app.include_router(finetuning_controller.router, prefix="/api")
app.include_router(rag_controller.router, prefix="/api")
app.include_router(auditoria_controller.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "MedAssist API"}
