#!/usr/bin/env python3
"""
Script 3 — Extração de Consumo e Billing (Camada E: Impacto Econômico)

Coleta:
  - Ciclos de billing da enterprise
  - Consumo diário de ACUs (total e por produto: devin, cascade, terminal)
  - Consumo diário por organização
  - Consumo por usuário (v2)

Saída:
  - output/consumption_cycles.json
  - output/consumption_daily.json
  - output/consumption_daily_by_org.json
  - output/consumption_summary.json

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/extract_consumption.py
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
    ORG_IDS,
    OUTPUT_DIR,
)
from scripts.api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("extract_consumption")


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


# ─── Ciclos de Billing ─────────────────────────────────────────────────────

def extract_consumption_cycles_v2(client: DevinAPIClient) -> list:
    """
    GET /v2/enterprise/consumption/cycles
    Retorna todos os ciclos de billing desde o início da enterprise.
    """
    logger.info("Extraindo ciclos de billing (v2)...")
    data = client.get(f"{BASE_URL_V2}/consumption/cycles")
    return data if isinstance(data, list) else data.get("items", [data])


def extract_consumption_cycles_v3(client: DevinAPIClient) -> list:
    """
    GET /v3/enterprise/consumption/cycles
    Retorna ciclos de billing via v3.
    """
    logger.info("Extraindo ciclos de billing (v3)...")
    data = client.get(f"{BASE_URL_V3}/consumption/cycles")
    return data if isinstance(data, list) else data.get("items", [data])


# ─── Consumo Diário ────────────────────────────────────────────────────────

def extract_daily_consumption_v2(client: DevinAPIClient) -> dict:
    """
    GET /v2/enterprise/consumption/daily
    Retorna consumo diário com breakdown por data, organização e usuário.
    Nota: Timezone PST (usar T08:00:00Z para alinhar com dashboard).
    """
    logger.info("Extraindo consumo diário (v2)...")

    # Ajustar para timezone PST (08:00 UTC)
    start_pst = DEFAULT_START_ISO.replace("T00:00:00Z", "T08:00:00Z")
    end_pst = DEFAULT_END_ISO.replace("T00:00:00Z", "T08:00:00Z")

    params = {
        "start_date": start_pst if "T08:" in start_pst else DEFAULT_START_ISO,
        "end_date": end_pst if "T08:" in end_pst else DEFAULT_END_ISO,
    }
    if ORG_IDS:
        params["org_ids"] = ORG_IDS

    return client.get(f"{BASE_URL_V2}/consumption/daily", params=params)


def extract_daily_consumption_v3(client: DevinAPIClient) -> dict:
    """
    GET /v3/enterprise/consumption/daily
    Retorna consumo diário com breakdown por produto (devin, cascade, terminal).
    """
    logger.info("Extraindo consumo diário (v3)...")
    params = {}
    # v3 pode usar time_after/time_before ou start_date/end_date
    return client.get(f"{BASE_URL_V3}/consumption/daily", params=params)


def extract_daily_consumption_by_org_v3(client: DevinAPIClient) -> dict:
    """
    GET /v3/enterprise/consumption/daily-organizations
    Retorna consumo diário detalhado por organização.
    """
    logger.info("Extraindo consumo diário por organização (v3)...")
    return client.get(f"{BASE_URL_V3}/consumption/daily-organizations")


# ─── Resumo de Consumo ─────────────────────────────────────────────────────

def generate_consumption_summary(daily_data: dict, cycles: list) -> dict:
    """Gera resumo estatístico do consumo."""
    summary = {
        "periodo": {
            "inicio": DEFAULT_START_ISO,
            "fim": DEFAULT_END_ISO,
        },
        "total_billing_cycles": len(cycles),
    }

    # Processar consumption_by_date (v2 format)
    by_date = daily_data.get("consumption_by_date", {})
    if isinstance(by_date, dict):
        daily_values = list(by_date.values())
        if daily_values:
            # Pode ser número direto ou dict com breakdown
            total_acus = 0
            for val in daily_values:
                if isinstance(val, (int, float)):
                    total_acus += val
                elif isinstance(val, dict):
                    total_acus += val.get("total", val.get("acus", 0))

            summary["total_acus_periodo"] = round(total_acus, 2)
            summary["dias_com_consumo"] = len([v for v in daily_values if v])
            summary["media_acu_por_dia"] = (
                round(total_acus / len(daily_values), 2) if daily_values else 0
            )

    # Processar consumption_by_org_id (v2 format)
    by_org = daily_data.get("consumption_by_org_id", {})
    if isinstance(by_org, dict):
        summary["consumo_por_organizacao"] = {
            org_id: round(val, 2) if isinstance(val, (int, float)) else val
            for org_id, val in by_org.items()
        }

    # Processar consumption_by_user (v2 format)
    by_user = daily_data.get("consumption_by_user", {})
    if isinstance(by_user, dict):
        summary["total_usuarios_com_consumo"] = len(by_user)
        if by_user:
            user_values = [
                v if isinstance(v, (int, float)) else 0
                for v in by_user.values()
            ]
            summary["top_5_usuarios_consumo"] = dict(
                sorted(by_user.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:5]
            )

    return summary


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    client = DevinAPIClient()

    logger.info(f"Período de coleta: {DEFAULT_START_ISO} → {DEFAULT_END_ISO}")

    # Ciclos de billing
    try:
        cycles = extract_consumption_cycles_v3(client)
    except Exception as e:
        logger.warning(f"Falha na v3: {e}. Tentando v2...")
        cycles = extract_consumption_cycles_v2(client)
    save_json(cycles, "consumption_cycles.json")

    # Consumo diário
    try:
        daily_v3 = extract_daily_consumption_v3(client)
        save_json(daily_v3, "consumption_daily_v3.json")
    except Exception as e:
        logger.warning(f"Consumo diário v3 indisponível: {e}")

    daily_v2 = extract_daily_consumption_v2(client)
    save_json(daily_v2, "consumption_daily.json")

    # Consumo por organização (v3)
    try:
        daily_by_org = extract_daily_consumption_by_org_v3(client)
        save_json(daily_by_org, "consumption_daily_by_org.json")
    except Exception as e:
        logger.warning(f"Consumo por org v3 indisponível: {e}")

    # Resumo
    summary = generate_consumption_summary(daily_v2, cycles)
    save_json(summary, "consumption_summary.json")

    logger.info(f"Resumo de consumo: {summary.get('total_acus_periodo', 'N/A')} ACUs no período.")


if __name__ == "__main__":
    main()
