"""Controller de Auditoria - trilha de logs do sistema."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import LogAuditoria

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@router.get("/logs")
async def listar_logs(
    acao: str = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Lista logs de auditoria com filtro opcional por ação."""
    stmt = select(LogAuditoria).order_by(desc(LogAuditoria.criado_em))
    if acao:
        stmt = stmt.where(LogAuditoria.acao.ilike(f"%{acao}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "acao": log.acao,
            "detalhes": log.detalhes,
            "usuario": log.usuario,
            "criado_em": str(log.criado_em),
        }
        for log in logs
    ]


@router.get("/stats")
async def stats_auditoria(db: AsyncSession = Depends(get_db)):
    """Estatísticas dos logs de auditoria."""
    # Total
    total_result = await db.execute(select(func.count(LogAuditoria.id)))
    total = total_result.scalar()

    # Por ação
    stmt = (
        select(LogAuditoria.acao, func.count(LogAuditoria.id))
        .group_by(LogAuditoria.acao)
        .order_by(desc(func.count(LogAuditoria.id)))
    )
    result = await db.execute(stmt)
    por_acao = {row[0]: row[1] for row in result.all()}

    # Por usuário
    stmt_usr = (
        select(LogAuditoria.usuario, func.count(LogAuditoria.id))
        .group_by(LogAuditoria.usuario)
        .order_by(desc(func.count(LogAuditoria.id)))
    )
    result_usr = await db.execute(stmt_usr)
    por_usuario = {(row[0] or "sistema"): row[1] for row in result_usr.all()}

    return {
        "total": total,
        "por_acao": por_acao,
        "por_usuario": por_usuario,
    }


@router.get("/categorias")
async def categorias_auditoria(db: AsyncSession = Depends(get_db)):
    """Lista todas as categorias (ações) disponíveis."""
    stmt = select(LogAuditoria.acao).distinct().order_by(LogAuditoria.acao)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]
