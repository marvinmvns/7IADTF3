#!/usr/bin/env python3
"""
Script 5 — Extração de Membros e Organizações (Dimensões de Contexto)

Coleta:
  - Lista de organizações da enterprise
  - Lista de membros (usuários) da enterprise
  - Roles e permissões

Esses dados servem como dimensões para cruzar com sessões, consumo e métricas.

Saída:
  - output/organizations.json
  - output/members.json
  - output/members_orgs_summary.json

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/extract_members_orgs.py
"""

import json
import logging
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    BASE_URL_V2,
    BASE_URL_V3,
    OUTPUT_DIR,
)
from scripts.api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("extract_members_orgs")


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


# ─── Organizações ──────────────────────────────────────────────────────────

def extract_organizations_v2(client: DevinAPIClient) -> list:
    """GET /v2/enterprise/organizations"""
    logger.info("Extraindo organizações (v2)...")
    data = client.get(f"{BASE_URL_V2}/organizations")
    if isinstance(data, list):
        return data
    return data.get("organizations", data.get("items", []))


def extract_organizations_v3(client: DevinAPIClient) -> list:
    """GET /v3/enterprise/organizations"""
    logger.info("Extraindo organizações (v3)...")
    data = client.get(f"{BASE_URL_V3}/organizations")
    if isinstance(data, list):
        return data
    return data.get("organizations", data.get("items", []))


# ─── Membros ───────────────────────────────────────────────────────────────

def extract_members_v2(client: DevinAPIClient) -> list:
    """GET /v2/enterprise/members"""
    logger.info("Extraindo membros (v2)...")
    return client.get_all_pages_offset(f"{BASE_URL_V2}/members")


def extract_members_v3(client: DevinAPIClient) -> list:
    """GET /v3/enterprise/users"""
    logger.info("Extraindo membros (v3)...")
    data = client.get(f"{BASE_URL_V3}/users")
    if isinstance(data, list):
        return data
    return data.get("users", data.get("items", []))


# ─── Resumo ────────────────────────────────────────────────────────────────

def generate_summary(orgs: list, members: list) -> dict:
    """Gera resumo de membros e organizações."""
    role_counts = Counter()
    for member in members:
        role = member.get("role") or member.get("enterprise_role", "unknown")
        role_counts[role] += 1

    return {
        "total_organizacoes": len(orgs),
        "total_membros": len(members),
        "distribuicao_por_role": dict(role_counts),
        "organizacoes": [
            {
                "id": org.get("org_id") or org.get("id"),
                "name": org.get("name") or org.get("display_name", "N/A"),
            }
            for org in orgs
        ],
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    client = DevinAPIClient()

    # Organizações
    try:
        orgs = extract_organizations_v3(client)
    except Exception as e:
        logger.warning(f"Falha na v3: {e}. Tentando v2...")
        orgs = extract_organizations_v2(client)
    save_json(orgs, "organizations.json")

    # Membros
    try:
        members = extract_members_v3(client)
    except Exception as e:
        logger.warning(f"Falha na v3: {e}. Tentando v2...")
        members = extract_members_v2(client)
    save_json(members, "members.json")

    # Resumo
    summary = generate_summary(orgs, members)
    save_json(summary, "members_orgs_summary.json")

    logger.info(f"Extração concluída: {len(orgs)} orgs, {len(members)} membros.")


if __name__ == "__main__":
    main()
