"""Logger centralizado para auditoria e rastreamento."""
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import LogAuditoria

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("medassist")


async def registrar_log(db: AsyncSession, acao: str, detalhes: str, usuario: str = "sistema"):
    log = LogAuditoria(acao=acao, detalhes=detalhes, usuario=usuario)
    db.add(log)
    await db.commit()
    logger.info(f"[{acao}] {detalhes} (por {usuario})")
