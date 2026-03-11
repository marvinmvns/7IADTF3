"""MedAssist - Assistente Médico Virtual | Ponto de entrada FastAPI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.controllers import (
    paciente_controller,
    prontuario_controller,
    triagem_controller,
    chat_controller,
    config_controller,
    scraping_controller,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="MedAssist - Assistente Médico Virtual",
    description="API do assistente médico com triagem, chat IA, scraping e TTS/STT",
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "MedAssist API"}
