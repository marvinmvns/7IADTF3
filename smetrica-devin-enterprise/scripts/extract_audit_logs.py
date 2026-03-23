#!/usr/bin/env python3
"""
Script 4 — Extração de Audit Logs (Camada C: Qualidade, Governança e Risco)

Coleta:
  - Logs de auditoria enterprise (ações de usuários, sessões, configurações)
  - Eventos de segurança e compliance
  - Trilha de rastreabilidade

Saída:
  - output/audit_logs.json
  - output/audit_logs.csv
  - output/audit_logs_summary.json

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/extract_audit_logs.py
"""

import csv
import json
import logging
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    BASE_URL_V2,
    BASE_URL_V3,
    ORG_IDS,
    OUTPUT_DIR,
    DEFAULT_START_ISO,
    DEFAULT_END_ISO,
)
from scripts.api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("extract_audit_logs")


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


# ─── Extração via API v2 ───────────────────────────────────────────────────

def extract_audit_logs_v2(client: DevinAPIClient) -> list:
    """
    GET /v2/enterprise/audit-logs
    Retorna logs de auditoria da enterprise inteira.
    Paginação via before/after cursors.
    """
    logger.info("Extraindo audit logs (v2)...")
    all_logs = []
    params = {"limit": 100}

    while True:
        data = client.get(f"{BASE_URL_V2}/audit-logs", params=params)
        logs = data.get("audit_logs", [])
        if not logs:
            break

        all_logs.extend(logs)
        logger.info(f"Coletados {len(all_logs)} audit logs até agora...")

        # Usar o último audit_log_id como cursor "before"
        last_id = logs[-1].get("audit_log_id")
        if not last_id or len(logs) < params["limit"]:
            break
        params["before"] = last_id

    logger.info(f"Total de audit logs coletados: {len(all_logs)}")
    return all_logs


# ─── Extração via API v3 (por organização) ─────────────────────────────────

def extract_audit_logs_v3(client: DevinAPIClient, org_ids: list = None) -> list:
    """
    GET /v3/enterprise/organizations/{org_id}/audit-logs
    Coleta audit logs por organização (v3).
    """
    target_orgs = org_ids or ORG_IDS or []
    if not target_orgs:
        logger.warning("Nenhum org_id fornecido para audit logs v3. Use v2 ou configure DEVIN_ORG_IDS.")
        return []

    all_logs = []
    for org_id in target_orgs:
        logger.info(f"Extraindo audit logs da organização {org_id} (v3)...")
        try:
            logs = client.get_all_pages_cursor(
                f"{BASE_URL_V3}/organizations/{org_id}/audit-logs"
            )
            for log in logs:
                log["org_id"] = org_id  # Enriquecer com org_id
            all_logs.extend(logs)
        except Exception as e:
            logger.error(f"Erro ao coletar audit logs da org {org_id}: {e}")

    return all_logs


# ─── Processamento ─────────────────────────────────────────────────────────

def generate_audit_summary(logs: list) -> dict:
    """Gera resumo dos audit logs para governança."""
    if not logs:
        return {"total_logs": 0, "message": "Nenhum audit log encontrado."}

    # Contar por tipo de ação (se disponível)
    action_counts = Counter()
    actor_counts = Counter()

    for log in logs:
        action = log.get("action") or log.get("event_type") or log.get("type", "unknown")
        action_counts[action] += 1

        actor = log.get("actor_id") or log.get("user_id") or log.get("actor", "unknown")
        actor_counts[actor] += 1

    return {
        "periodo": {
            "inicio": DEFAULT_START_ISO,
            "fim": DEFAULT_END_ISO,
        },
        "total_logs": len(logs),
        "distribuicao_por_acao": dict(action_counts.most_common(20)),
        "top_10_atores": dict(actor_counts.most_common(10)),
        "total_atores_unicos": len(actor_counts),
    }


def audit_logs_to_csv(logs: list, filename: str):
    """Exporta audit logs para CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)

    if not logs:
        logger.warning("Nenhum audit log para exportar.")
        return

    # Coletar todas as chaves únicas
    all_keys = set()
    for log in logs:
        all_keys.update(log.keys())
    fields = sorted(all_keys)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for log in logs:
            writer.writerow(log)

    logger.info(f"CSV exportado: {path} ({len(logs)} linhas)")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    client = DevinAPIClient()

    logger.info("Iniciando extração de audit logs...")

    # Tenta v2 primeiro (enterprise-wide, sem necessidade de org_id)
    logs_v2 = extract_audit_logs_v2(client)

    # Se tiver org_ids, também coleta via v3
    logs_v3 = []
    if ORG_IDS:
        try:
            logs_v3 = extract_audit_logs_v3(client)
        except Exception as e:
            logger.warning(f"Falha ao coletar audit logs v3: {e}")

    # Consolidar (v2 como base, v3 como complemento)
    all_logs = logs_v2
    if logs_v3:
        # Adicionar logs v3 que não estejam no v2 (por audit_log_id)
        existing_ids = {log.get("audit_log_id") for log in all_logs if log.get("audit_log_id")}
        for log in logs_v3:
            if log.get("audit_log_id") not in existing_ids:
                all_logs.append(log)

    # Salvar
    save_json(all_logs, "audit_logs.json")
    audit_logs_to_csv(all_logs, "audit_logs.csv")

    # Resumo
    summary = generate_audit_summary(all_logs)
    save_json(summary, "audit_logs_summary.json")

    logger.info(f"Extração de audit logs concluída: {len(all_logs)} registros.")


if __name__ == "__main__":
    main()
