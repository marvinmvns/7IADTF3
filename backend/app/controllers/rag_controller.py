"""Controller RAG - gerenciamento da base de conhecimento vetorial."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.rag.rag_service import (
    indexar_tudo, indexar_dados_medicos, indexar_dataset,
    indexar_prontuarios, buscar_contexto, stats_vector_store,
)
from app.utils.logger import registrar_log

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/indexar")
async def indexar_todas_fontes(db: AsyncSession = Depends(get_db)):
    """Indexa todas as fontes de dados no vector store."""
    resultado = await indexar_tudo(db)
    await registrar_log(db, "rag_indexacao", f"Total: {resultado['total_documentos']} docs")
    return resultado


@router.post("/indexar/dados-medicos")
async def indexar_fonte_dados_medicos(db: AsyncSession = Depends(get_db)):
    """Indexa apenas dados médicos (scraping)."""
    return await indexar_dados_medicos(db)


@router.post("/indexar/dataset")
async def indexar_fonte_dataset(db: AsyncSession = Depends(get_db)):
    """Indexa apenas o dataset de fine-tuning."""
    return await indexar_dataset(db)


@router.post("/indexar/prontuarios")
async def indexar_fonte_prontuarios(db: AsyncSession = Depends(get_db)):
    """Indexa apenas os prontuários."""
    return await indexar_prontuarios(db)


@router.get("/buscar")
async def buscar(pergunta: str, n: int = 5, tipo: str = None):
    """Busca documentos similares no vector store (para debug/teste)."""
    resultados = buscar_contexto(pergunta, n_resultados=n, filtro_tipo=tipo)
    return {"pergunta": pergunta, "resultados": resultados}


@router.get("/stats")
async def obter_stats():
    """Estatísticas do vector store."""
    return stats_vector_store()
