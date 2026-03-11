"""Controller de Scraping - busca de dados médicos."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import ScrapingRequest, DadoMedicoOut
from app.services.scraping.scraping_service import ScrapingService
from app.utils.logger import registrar_log

router = APIRouter(prefix="/scraping", tags=["Scraping"])


@router.post("/buscar", response_model=list[DadoMedicoOut])
async def buscar_dados(req: ScrapingRequest, db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    dados = await service.buscar(req.fonte, req.termo, req.max_resultados)
    await registrar_log(db, "scraping", f"Fonte: {req.fonte}, Termo: {req.termo}")
    return dados


@router.get("/dados", response_model=list[DadoMedicoOut])
async def listar_dados(fonte: str = None, skip: int = 0, limit: int = 50,
                       db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    return await service.listar(fonte, skip, limit)


@router.post("/agente")
async def executar_agente(termo: str, db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    resultado = await service.agente_navegacao(termo)
    await registrar_log(db, "agente_navegacao", f"Termo: {termo}")
    return resultado
