"""Controller de Fine-Tuning - endpoints REST."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import FineTuningJob, DatasetEntry
from app.schemas.schemas import (
    FineTuningStart, FineTuningJobOut,
    DatasetEntryCreate, DatasetEntryOut,
)
from app.services.finetuning_service import (
    MODELOS_DISPONIVEIS, iniciar_finetuning, cancelar_job,
    importar_dataset_json, gerar_dataset_por_doenca,
)
from app.utils.logger import registrar_log

router = APIRouter(prefix="/finetuning", tags=["Fine-Tuning"])


# --- Modelos disponíveis ---
@router.get("/modelos")
async def listar_modelos():
    """Lista modelos disponíveis para fine-tuning."""
    return MODELOS_DISPONIVEIS


# --- Jobs ---
@router.post("/iniciar", response_model=FineTuningJobOut)
async def iniciar(config: FineTuningStart, db: AsyncSession = Depends(get_db)):
    """Inicia um novo job de fine-tuning."""
    # Verifica se já há job em andamento
    result = await db.execute(
        select(FineTuningJob).where(FineTuningJob.status == "treinando")
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Já existe um treinamento em andamento.")

    try:
        job = await iniciar_finetuning(db, config.model_dump())
        await registrar_log(db, "finetuning_iniciado", f"Job #{job.id} - Modelo: {config.modelo_base}")
        return job
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/jobs", response_model=list[FineTuningJobOut])
async def listar_jobs(db: AsyncSession = Depends(get_db)):
    """Lista todos os jobs de fine-tuning."""
    result = await db.execute(
        select(FineTuningJob).order_by(desc(FineTuningJob.criado_em))
    )
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=FineTuningJobOut)
async def obter_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Obtém status de um job específico."""
    result = await db.execute(
        select(FineTuningJob).where(FineTuningJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return job


@router.post("/jobs/{job_id}/cancelar")
async def cancelar(job_id: int, db: AsyncSession = Depends(get_db)):
    """Cancela um job em execução."""
    await cancelar_job(job_id, db)
    await registrar_log(db, "finetuning_cancelado", f"Job #{job_id} cancelado")
    return {"status": "cancelado"}


# --- Dataset ---
@router.get("/dataset", response_model=list[DatasetEntryOut])
async def listar_dataset(db: AsyncSession = Depends(get_db)):
    """Lista todas as entradas do dataset."""
    result = await db.execute(
        select(DatasetEntry).order_by(desc(DatasetEntry.criado_em))
    )
    return result.scalars().all()


@router.post("/dataset", response_model=DatasetEntryOut)
async def adicionar_entrada(entry: DatasetEntryCreate, db: AsyncSession = Depends(get_db)):
    """Adiciona uma nova entrada ao dataset."""
    obj = DatasetEntry(**entry.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await registrar_log(db, "dataset_entrada_adicionada", f"Entrada #{obj.id} adicionada ao dataset")
    return obj


@router.delete("/dataset/{entry_id}")
async def remover_entrada(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Remove (desativa) uma entrada do dataset."""
    result = await db.execute(
        select(DatasetEntry).where(DatasetEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entrada não encontrada.")
    entry.ativo = False
    await db.commit()
    await registrar_log(db, "dataset_entrada_removida", f"Entrada #{entry_id} removida do dataset")
    return {"status": "removido"}


@router.post("/dataset/importar-json")
async def importar_json(db: AsyncSession = Depends(get_db)):
    """Importa o dataset sintético JSON para o banco."""
    entries = await importar_dataset_json(db)
    await registrar_log(db, "dataset_importado", f"{len(entries)} entradas importadas via JSON")
    return {"importados": len(entries)}


@router.post("/dataset/gerar")
async def gerar_dataset_doenca(doenca: str, db: AsyncSession = Depends(get_db)):
    """Gera entradas de dataset automaticamente buscando informações sobre uma doença."""
    try:
        entries = await gerar_dataset_por_doenca(db, doenca)
    except Exception as e:
        raise HTTPException(502, f"Erro ao gerar dataset: {type(e).__name__}: {str(e)}")
    await registrar_log(db, "dataset_gerado", f"Doença: {doenca}, Entradas: {len(entries)}")
    return {"gerados": len(entries), "doenca": doenca}


@router.get("/modelo-ativo")
async def modelo_ativo(db: AsyncSession = Depends(get_db)):
    """Retorna info do modelo fine-tuned ativo (usado nas respostas do chat)."""
    from app.services.finetuned_inference import get_finetuned_model_info
    info = await get_finetuned_model_info(db)
    if not info:
        return {"ativo": False, "msg": "Nenhum modelo fine-tuned disponível"}
    return {"ativo": True, **info}


@router.get("/dataset/stats")
async def dataset_stats(db: AsyncSession = Depends(get_db)):
    """Estatísticas do dataset."""
    result = await db.execute(
        select(DatasetEntry).where(DatasetEntry.ativo == True)
    )
    entries = result.scalars().all()

    categorias: dict[str, int] = {}
    for e in entries:
        cat = e.categoria or "sem_categoria"
        categorias[cat] = categorias.get(cat, 0) + 1

    return {
        "total": len(entries),
        "categorias": categorias,
    }
