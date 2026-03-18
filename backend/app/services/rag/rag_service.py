"""Serviço RAG - Retrieval-Augmented Generation para respostas médicas contextualizadas.

Usa ChromaDB como vector store local e sentence-transformers para embeddings.
Indexa dados de múltiplas fontes: dados_medicos (scraping), dataset (fine-tuning),
prontuários e protocolos médicos.
"""
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

_BRT = timezone(timedelta(hours=-3))


def _now_brt():
    return datetime.now(_BRT).replace(tzinfo=None)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DadoMedico, DatasetEntry, Prontuario, Paciente

logger = logging.getLogger("medassist.rag")

CHROMA_DIR = Path(__file__).parent.parent.parent.parent / "models" / "chroma_db"
COLLECTION_NAME = "medassist_docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Singleton do vector store
_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_fn():
    """Retorna função de embedding usando sentence-transformers."""
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            _embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
            logger.info(f"Embedding model carregado: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.warning(f"Falha ao carregar embedding model: {e}. Usando default.")
            _embedding_fn = None
    return _embedding_fn


def _get_collection():
    """Retorna a collection do ChromaDB (cria se não existir)."""
    global _chroma_client, _collection
    if _collection is None:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        emb_fn = _get_embedding_fn()
        kwargs = {"name": COLLECTION_NAME}
        if emb_fn:
            kwargs["embedding_function"] = emb_fn

        _collection = _chroma_client.get_or_create_collection(
            **kwargs,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' pronta. Docs: {_collection.count()}")
    return _collection


async def indexar_dados_medicos(db: AsyncSession) -> dict:
    """Indexa dados médicos (scraping) no vector store."""
    result = await db.execute(select(DadoMedico))
    dados = result.scalars().all()

    if not dados:
        return {"fonte": "dados_medicos", "indexados": 0, "msg": "Nenhum dado médico encontrado"}

    collection = _get_collection()
    docs, metas, ids = [], [], []

    for d in dados:
        doc_id = f"med_{d.id}"
        texto = f"{d.titulo}\n\n{d.conteudo}"
        docs.append(texto)
        metas.append({
            "fonte": d.fonte,
            "tipo": "dado_medico",
            "titulo": d.titulo[:200],
            "url": d.url or "",
            "categoria": d.categoria or "",
            "coletado_em": str(d.coletado_em),
        })
        ids.append(doc_id)

    collection.upsert(documents=docs, metadatas=metas, ids=ids)
    logger.info(f"Indexados {len(docs)} dados médicos")
    return {"fonte": "dados_medicos", "indexados": len(docs)}


async def indexar_dataset(db: AsyncSession) -> dict:
    """Indexa dataset de fine-tuning no vector store."""
    result = await db.execute(
        select(DatasetEntry).where(DatasetEntry.ativo == True)
    )
    entries = result.scalars().all()

    if not entries:
        return {"fonte": "dataset", "indexados": 0, "msg": "Dataset vazio"}

    collection = _get_collection()
    docs, metas, ids = [], [], []

    for e in entries:
        doc_id = f"ds_{e.id}"
        texto = f"Pergunta: {e.pergunta}\n"
        if e.contexto:
            texto += f"Contexto: {e.contexto}\n"
        texto += f"Resposta: {e.resposta}"

        docs.append(texto)
        metas.append({
            "fonte": "dataset_treinamento",
            "tipo": "protocolo",
            "titulo": e.pergunta[:200],
            "url": "",
            "categoria": e.categoria or "protocolo_medico",
            "coletado_em": str(e.criado_em),
        })
        ids.append(doc_id)

    collection.upsert(documents=docs, metadatas=metas, ids=ids)
    logger.info(f"Indexados {len(docs)} entradas do dataset")
    return {"fonte": "dataset", "indexados": len(docs)}


async def indexar_prontuarios(db: AsyncSession) -> dict:
    """Indexa prontuários anonimizados no vector store."""
    result = await db.execute(
        select(Prontuario, Paciente)
        .join(Paciente, Prontuario.paciente_id == Paciente.id)
    )
    rows = result.all()

    if not rows:
        return {"fonte": "prontuarios", "indexados": 0, "msg": "Nenhum prontuário encontrado"}

    collection = _get_collection()
    docs, metas, ids = [], [], []

    for pront, pac in rows:
        doc_id = f"pront_{pront.id}"
        # Anonimiza: não inclui nome/CPF no documento indexado
        texto = (
            f"Diagnóstico: {pront.diagnostico}\n"
            f"Medicamentos: {pront.medicamentos or 'N/A'}\n"
            f"Alergias: {pront.alergias or 'N/A'}\n"
            f"Observações: {pront.observacoes or 'N/A'}\n"
            f"Médico: {pront.medico_responsavel}"
        )
        docs.append(texto)
        metas.append({
            "fonte": "prontuario",
            "tipo": "prontuario",
            "titulo": f"Prontuário - {pront.diagnostico[:100]}",
            "url": "",
            "categoria": "prontuario",
            "coletado_em": str(pront.criado_em),
        })
        ids.append(doc_id)

    collection.upsert(documents=docs, metadatas=metas, ids=ids)
    logger.info(f"Indexados {len(docs)} prontuários")
    return {"fonte": "prontuarios", "indexados": len(docs)}


async def indexar_tudo(db: AsyncSession) -> dict:
    """Indexa todas as fontes de dados."""
    resultados = []
    resultados.append(await indexar_dados_medicos(db))
    resultados.append(await indexar_dataset(db))
    resultados.append(await indexar_prontuarios(db))

    collection = _get_collection()
    total = collection.count()
    return {
        "total_documentos": total,
        "fontes": resultados,
        "atualizado_em": _now_brt().isoformat(),
    }


def buscar_contexto(pergunta: str, n_resultados: int = 5, filtro_tipo: str = None) -> list[dict]:
    """Busca documentos relevantes para a pergunta no vector store."""
    collection = _get_collection()

    if collection.count() == 0:
        return []

    where = None
    if filtro_tipo:
        where = {"tipo": filtro_tipo}

    results = collection.query(
        query_texts=[pergunta],
        n_results=min(n_resultados, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    contextos = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Cosine distance: 0 = idêntico, 2 = oposto. Filtra irrelevantes.
            similaridade = 1 - dist
            if similaridade < 0.15:
                continue

            contextos.append({
                "conteudo": doc,
                "fonte": meta.get("fonte", "desconhecida"),
                "tipo": meta.get("tipo", ""),
                "titulo": meta.get("titulo", ""),
                "url": meta.get("url", ""),
                "categoria": meta.get("categoria", ""),
                "similaridade": round(similaridade, 3),
            })

    return contextos


def formatar_contexto_para_prompt(contextos: list[dict], max_chars: int = 3000) -> str:
    """Formata os contextos recuperados para inserir no prompt do LLM."""
    if not contextos:
        return ""

    partes = []
    chars = 0
    for i, ctx in enumerate(contextos, 1):
        fonte_label = _fonte_label(ctx["fonte"])
        bloco = (
            f"[Fonte {i}: {fonte_label}]\n"
            f"{ctx['conteudo']}\n"
        )
        if chars + len(bloco) > max_chars:
            break
        partes.append(bloco)
        chars += len(bloco)

    return "\n---\n".join(partes)


def formatar_fontes_resposta(contextos: list[dict]) -> str:
    """Formata as fontes usadas para a linha de explainability."""
    if not contextos:
        return ""

    fontes = []
    seen = set()
    for ctx in contextos:
        label = _fonte_label(ctx["fonte"])
        titulo = ctx.get("titulo", "")
        url = ctx.get("url", "")
        key = f"{label}:{titulo[:50]}"
        if key not in seen:
            seen.add(key)
            entry = f"{label}"
            if titulo:
                entry += f" - {titulo[:80]}"
            if url:
                entry += f" ({url})"
            fontes.append(entry)

    return " | ".join(fontes[:3])


def _fonte_label(fonte: str) -> str:
    """Converte identificador de fonte em label legível."""
    labels = {
        "pubmed": "PubMed",
        "medlineplus": "MedlinePlus",
        "bvs": "BVS/BIREME",
        "drauzio": "Drauzio Varella",
        "mayo": "Mayo Clinic",
        "datasus": "DataSUS",
        "openfda": "OpenFDA",
        "agente_navegacao": "Navegação Automática",
        "dataset_treinamento": "Protocolo Hospitalar",
        "prontuario": "Prontuário Clínico",
    }
    return labels.get(fonte, fonte.replace("_", " ").title())


async def buscar_contexto_paciente(db: AsyncSession, paciente_id: int) -> str:
    """Busca dados completos de um paciente específico via query direta no banco.

    Retorna dados formatados de prontuários, triagens e alergias do paciente.
    Isso é uma consulta direta (não semântica) para garantir dados exatos.
    """
    from app.models.models import Triagem

    # Buscar paciente
    result = await db.execute(select(Paciente).where(Paciente.id == paciente_id))
    paciente = result.scalar_one_or_none()
    if not paciente:
        logger.warning(f"Paciente {paciente_id} não encontrado para contexto")
        return ""

    # Buscar prontuários
    result = await db.execute(
        select(Prontuario)
        .where(Prontuario.paciente_id == paciente_id)
        .order_by(Prontuario.data_consulta.desc())
    )
    prontuarios = result.scalars().all()

    # Buscar triagens
    result = await db.execute(
        select(Triagem)
        .where(Triagem.paciente_id == paciente_id)
        .order_by(Triagem.criado_em.desc())
        .limit(5)
    )
    triagens = result.scalars().all()

    # Montar prontuários detalhados (ordem cronológica)
    prontuarios_info = []
    diagnosticos = []
    medicamentos_set = set()
    alergias_set = set()
    for p in prontuarios:
        if p.diagnostico:
            diagnosticos.append(p.diagnostico)
        if p.medicamentos:
            medicamentos_set.add(p.medicamentos)
        if p.alergias:
            alergias_set.add(p.alergias)
        data_str = p.data_consulta.strftime('%d/%m/%Y') if p.data_consulta else 'N/A'
        info = f"[{data_str}] Médico: {p.medico_responsavel} | Diagnóstico: {p.diagnostico}"
        if p.medicamentos:
            info += f" | Medicamentos: {p.medicamentos}"
        if p.observacoes:
            info += f" | Obs: {p.observacoes}"
        prontuarios_info.append(info)

    # Montar triagens recentes
    triagens_info = []
    for t in triagens:
        info = f"[{t.criado_em.strftime('%d/%m/%Y')}] Risco: {t.classificacao_risco} | Sintomas: {t.sintomas}"
        if t.pressao_arterial:
            info += f" | PA: {t.pressao_arterial}"
        if t.temperatura:
            info += f" | Temp: {t.temperatura}°C"
        if t.frequencia_cardiaca:
            info += f" | FC: {t.frequencia_cardiaca}bpm"
        if t.saturacao:
            info += f" | SpO2: {t.saturacao}%"
        triagens_info.append(info)

    contexto = (
        f"--- DADOS DO PACIENTE ---\n"
        f"Nome: {paciente.nome}\n"
        f"Sexo: {paciente.sexo} | Nascimento: {paciente.data_nascimento}\n"
        f"Alergias: {'; '.join(alergias_set) if alergias_set else 'Nenhuma registrada'}\n"
        f"Medicamentos em uso: {'; '.join(medicamentos_set) if medicamentos_set else 'Nenhum registrado'}\n\n"
        f"Prontuários (histórico de atendimentos):\n"
        f"{chr(10).join(prontuarios_info) if prontuarios_info else 'Nenhum registrado'}\n\n"
        f"Triagens recentes:\n"
        f"{chr(10).join(triagens_info) if triagens_info else 'Nenhuma registrada'}\n"
        f"--- FIM DADOS DO PACIENTE ---"
    )

    logger.info(f"Contexto do paciente {paciente_id} ({paciente.nome}) carregado: "
                f"{len(prontuarios)} prontuários, {len(triagens)} triagens")
    return contexto


def stats_vector_store() -> dict:
    """Retorna estatísticas do vector store."""
    collection = _get_collection()
    total = collection.count()

    # Conta por tipo
    tipos = {}
    if total > 0:
        all_meta = collection.get(include=["metadatas"])
        if all_meta and all_meta["metadatas"]:
            for meta in all_meta["metadatas"]:
                tipo = meta.get("tipo", "desconhecido")
                tipos[tipo] = tipos.get(tipo, 0) + 1

    return {
        "total_documentos": total,
        "por_tipo": tipos,
        "embedding_model": EMBEDDING_MODEL,
        "diretorio": str(CHROMA_DIR),
    }
