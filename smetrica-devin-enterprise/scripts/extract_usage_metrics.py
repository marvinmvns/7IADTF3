#!/usr/bin/env python3
"""
Script 1 — Extração de Métricas de Uso (Camada A: Adoção e Uso)

Coleta:
  - Sessões totais por período
  - Buscas totais por período
  - PRs abertas, fechadas e mergeadas
  - Usuários ativos diários (DAU), semanais (WAU) e mensais (MAU)
  - Métricas agregadas de uso (v2)

Saída:
  - output/usage_metrics.json
  - output/active_users_dau.json
  - output/active_users_wau.json
  - output/active_users_mau.json
  - output/pr_metrics.json

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/extract_usage_metrics.py
"""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    BASE_URL_V2,
    BASE_URL_V3,
    DEFAULT_START_ISO,
    DEFAULT_END_ISO,
    DEFAULT_TIME_AFTER,
    DEFAULT_TIME_BEFORE,
    ORG_IDS,
    OUTPUT_DIR,
)
from scripts.api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("extract_usage_metrics")


def save_json(data, filename):
    """Salva dados em arquivo JSON no diretório de saída."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


# ─── Extração via API v2 (Legacy) ──────────────────────────────────────────

def extract_usage_metrics_v2(client: DevinAPIClient) -> dict:
    """
    GET /v2/enterprise/metrics/usage
    Retorna sessões, buscas e PRs agregados.
    """
    logger.info("Extraindo métricas de uso agregadas (v2)...")
    params = {
        "start_date": DEFAULT_START_ISO,
        "end_date": DEFAULT_END_ISO,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS

    data = client.get(f"{BASE_URL_V2}/metrics/usage", params=params)
    return data


def extract_sessions_count_v2(client: DevinAPIClient) -> dict:
    """GET /v2/enterprise/metrics/sessions"""
    logger.info("Extraindo contagem de sessões (v2)...")
    params = {"start_date": DEFAULT_START_ISO, "end_date": DEFAULT_END_ISO}
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V2}/metrics/sessions", params=params)


def extract_searches_count_v2(client: DevinAPIClient) -> dict:
    """GET /v2/enterprise/metrics/searches"""
    logger.info("Extraindo contagem de buscas (v2)...")
    params = {"start_date": DEFAULT_START_ISO, "end_date": DEFAULT_END_ISO}
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V2}/metrics/searches", params=params)


def extract_pr_metrics_v2(client: DevinAPIClient) -> dict:
    """GET /v2/enterprise/metrics/prs"""
    logger.info("Extraindo métricas de PRs (v2)...")
    params = {"start_date": DEFAULT_START_ISO, "end_date": DEFAULT_END_ISO}
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V2}/metrics/prs", params=params)


# ─── Extração via API v3 (Atual) ───────────────────────────────────────────

def extract_dau(client: DevinAPIClient) -> list:
    """
    GET /v3/enterprise/metrics/dau
    Retorna usuários ativos diários no período.
    """
    logger.info("Extraindo DAU (Daily Active Users) via v3...")
    params = {
        "time_after": DEFAULT_TIME_AFTER,
        "time_before": DEFAULT_TIME_BEFORE,
        "min_sessions": 1,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V3}/metrics/dau", params=params)


def extract_wau(client: DevinAPIClient) -> list:
    """GET /v3/enterprise/metrics/wau"""
    logger.info("Extraindo WAU (Weekly Active Users) via v3...")
    params = {
        "time_after": DEFAULT_TIME_AFTER,
        "time_before": DEFAULT_TIME_BEFORE,
        "min_sessions": 1,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V3}/metrics/wau", params=params)


def extract_mau(client: DevinAPIClient) -> list:
    """GET /v3/enterprise/metrics/mau"""
    logger.info("Extraindo MAU (Monthly Active Users) via v3...")
    params = {
        "time_after": DEFAULT_TIME_AFTER,
        "time_before": DEFAULT_TIME_BEFORE,
        "min_sessions": 1,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS
    return client.get(f"{BASE_URL_V3}/metrics/mau", params=params)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    client = DevinAPIClient()

    logger.info(f"Período de coleta: {DEFAULT_START_ISO} → {DEFAULT_END_ISO}")
    logger.info(f"Organizações filtradas: {ORG_IDS or 'Todas'}")

    # v2 — Métricas agregadas
    usage = extract_usage_metrics_v2(client)
    save_json(usage, "usage_metrics.json")

    sessions_count = extract_sessions_count_v2(client)
    save_json(sessions_count, "sessions_count.json")

    searches_count = extract_searches_count_v2(client)
    save_json(searches_count, "searches_count.json")

    pr_metrics = extract_pr_metrics_v2(client)
    save_json(pr_metrics, "pr_metrics.json")

    # v3 — Usuários ativos
    dau = extract_dau(client)
    save_json(dau, "active_users_dau.json")

    wau = extract_wau(client)
    save_json(wau, "active_users_wau.json")

    mau = extract_mau(client)
    save_json(mau, "active_users_mau.json")

    logger.info("Extração de métricas de uso concluída com sucesso.")


if __name__ == "__main__":
    main()
