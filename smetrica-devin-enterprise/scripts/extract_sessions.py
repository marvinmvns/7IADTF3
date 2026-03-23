#!/usr/bin/env python3
"""
Script 2 — Extração de Sessões Enterprise (Camada A + B: Adoção e Eficiência)

Coleta todas as sessões da enterprise com detalhes completos, incluindo:
  - ID, título, status, status_detail
  - Usuário criador (user_id)
  - Organização (org_id)
  - ACUs consumidos
  - Pull Requests associadas (URL e estado)
  - Tags, playbook_id
  - Timestamps de criação e atualização
  - Sessões filhas e pai (workflow)
  - Flags: is_advanced, is_archived

Saída:
  - output/enterprise_sessions.json      (dados brutos)
  - output/enterprise_sessions.csv       (tabela para análise)
  - output/sessions_summary.json         (resumo estatístico)

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/extract_sessions.py
"""

import csv
import json
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    BASE_URL_V3_BETA,
    BASE_URL_V2,
    DEFAULT_START_ISO,
    DEFAULT_END_ISO,
    ORG_IDS,
    OUTPUT_DIR,
)
from scripts.api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("extract_sessions")


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


def epoch_to_iso(epoch_val):
    """Converte epoch seconds para string ISO 8601."""
    if not epoch_val:
        return None
    try:
        return datetime.fromtimestamp(epoch_val, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return str(epoch_val)


# ─── Extração via API v3 (Beta) ────────────────────────────────────────────

def extract_sessions_v3(client: DevinAPIClient) -> list:
    """
    GET /v3beta1/enterprise/sessions
    Retorna lista paginada de todas as sessões enterprise.
    """
    logger.info("Extraindo sessões enterprise via v3beta1...")
    params = {}
    if ORG_IDS:
        params["org_ids"] = ORG_IDS

    sessions = client.get_all_pages_cursor(
        f"{BASE_URL_V3_BETA}/sessions",
        params=params,
    )
    return sessions


# ─── Extração via API v2 (Fallback) ────────────────────────────────────────

def extract_sessions_v2(client: DevinAPIClient) -> list:
    """
    GET /v2/enterprise/sessions
    Fallback caso a v3beta1 não esteja disponível.
    """
    logger.info("Extraindo sessões enterprise via v2 (fallback)...")
    params = {
        "start_date": DEFAULT_START_ISO,
        "end_date": DEFAULT_END_ISO,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS

    sessions = client.get_all_pages_offset(
        f"{BASE_URL_V2}/sessions",
        params=params,
    )
    return sessions


# ─── Processamento e Enriquecimento ────────────────────────────────────────

def enrich_session(session: dict) -> dict:
    """Adiciona campos derivados a cada sessão para facilitar análise."""
    enriched = dict(session)

    # Converter timestamps
    enriched["created_at_iso"] = epoch_to_iso(session.get("created_at"))
    enriched["updated_at_iso"] = epoch_to_iso(session.get("updated_at"))

    # Duração estimada (updated_at - created_at)
    created = session.get("created_at")
    updated = session.get("updated_at")
    if created and updated and isinstance(created, (int, float)) and isinstance(updated, (int, float)):
        enriched["duration_seconds"] = max(0, updated - created)
        enriched["duration_hours"] = round(enriched["duration_seconds"] / 3600, 2)
    else:
        enriched["duration_seconds"] = None
        enriched["duration_hours"] = None

    # Contagem de PRs
    prs = session.get("pull_requests", [])
    enriched["pr_count"] = len(prs)
    enriched["pr_merged_count"] = sum(1 for pr in prs if pr.get("pr_state") == "merged")
    enriched["pr_open_count"] = sum(1 for pr in prs if pr.get("pr_state") == "open")
    enriched["pr_closed_count"] = sum(1 for pr in prs if pr.get("pr_state") == "closed")

    # Flag de sessão produtiva (gerou pelo menos 1 PR mergeada)
    enriched["is_productive"] = enriched["pr_merged_count"] > 0

    # ACU por PR mergeada (eficiência)
    acus = session.get("acus_consumed", 0) or 0
    enriched["acu_per_merged_pr"] = (
        round(acus / enriched["pr_merged_count"], 2)
        if enriched["pr_merged_count"] > 0
        else None
    )

    return enriched


def generate_summary(sessions: list) -> dict:
    """Gera resumo estatístico das sessões coletadas."""
    total = len(sessions)
    if total == 0:
        return {"total_sessions": 0, "message": "Nenhuma sessão encontrada no período."}

    status_counts = Counter(s.get("status") for s in sessions)
    status_detail_counts = Counter(s.get("status_detail") for s in sessions)

    total_acus = sum(s.get("acus_consumed", 0) or 0 for s in sessions)
    total_prs = sum(s.get("pr_count", 0) for s in sessions)
    total_merged = sum(s.get("pr_merged_count", 0) for s in sessions)
    productive = sum(1 for s in sessions if s.get("is_productive"))

    durations = [s["duration_hours"] for s in sessions if s.get("duration_hours") is not None]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else None

    unique_users = len(set(s.get("user_id") for s in sessions if s.get("user_id")))
    unique_orgs = len(set(s.get("org_id") for s in sessions if s.get("org_id")))

    return {
        "periodo": {
            "inicio": DEFAULT_START_ISO,
            "fim": DEFAULT_END_ISO,
        },
        "total_sessions": total,
        "sessoes_produtivas": productive,
        "taxa_produtividade": round(productive / total * 100, 1) if total > 0 else 0,
        "total_acus_consumidos": round(total_acus, 2),
        "acu_medio_por_sessao": round(total_acus / total, 2) if total > 0 else 0,
        "total_prs": total_prs,
        "total_prs_mergeadas": total_merged,
        "taxa_merge": round(total_merged / total_prs * 100, 1) if total_prs > 0 else 0,
        "acu_por_pr_mergeada": round(total_acus / total_merged, 2) if total_merged > 0 else None,
        "duracao_media_horas": avg_duration,
        "usuarios_unicos": unique_users,
        "organizacoes_unicas": unique_orgs,
        "distribuicao_status": dict(status_counts),
        "distribuicao_status_detail": dict(status_detail_counts),
    }


def sessions_to_csv(sessions: list, filename: str):
    """Exporta sessões para CSV para análise em planilha/BI."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)

    if not sessions:
        logger.warning("Nenhuma sessão para exportar em CSV.")
        return

    # Campos planos para CSV
    csv_fields = [
        "session_id", "title", "status", "status_detail",
        "user_id", "org_id", "acus_consumed",
        "created_at_iso", "updated_at_iso",
        "duration_hours", "pr_count", "pr_merged_count",
        "pr_open_count", "pr_closed_count",
        "is_productive", "acu_per_merged_pr",
        "is_advanced", "is_archived",
        "playbook_id", "parent_session_id",
        "tags",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for s in sessions:
            row = dict(s)
            row["tags"] = "; ".join(s.get("tags", []) or [])
            writer.writerow(row)

    logger.info(f"CSV exportado: {path} ({len(sessions)} linhas)")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    client = DevinAPIClient()

    logger.info(f"Período de coleta: {DEFAULT_START_ISO} → {DEFAULT_END_ISO}")

    # Tenta v3beta1 primeiro, fallback para v2
    try:
        raw_sessions = extract_sessions_v3(client)
    except Exception as e:
        logger.warning(f"Falha na v3beta1: {e}. Tentando v2...")
        raw_sessions = extract_sessions_v2(client)

    # Enriquecer sessões
    sessions = [enrich_session(s) for s in raw_sessions]

    # Salvar dados brutos enriquecidos
    save_json(sessions, "enterprise_sessions.json")

    # Exportar CSV
    sessions_to_csv(sessions, "enterprise_sessions.csv")

    # Gerar e salvar resumo
    summary = generate_summary(sessions)
    save_json(summary, "sessions_summary.json")

    logger.info(f"Resumo: {summary.get('total_sessions', 0)} sessões, "
                f"{summary.get('sessoes_produtivas', 0)} produtivas, "
                f"{summary.get('total_acus_consumidos', 0)} ACUs consumidos.")


if __name__ == "__main__":
    main()
