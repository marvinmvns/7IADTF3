#!/usr/bin/env python3
"""
Script 6 — Cálculo de Métricas Derivadas e Indicadores Compostos

Consome os dados brutos extraídos pelos scripts anteriores e calcula:
  - Camada A: Score de Adoção
  - Camada B: Score de Eficiência Operacional
  - Camada C: Score de Qualidade
  - Camada E: Indicadores de ROI
  - Score Consolidado de Maturidade

Pré-requisito:
  Executar antes os scripts de extração (extract_*.py).

Saída:
  - output/derived_metrics.json
  - output/roi_analysis.json
  - output/maturity_scorecard.json

Uso:
  python3 scripts/calculate_metrics.py [--dev-hour-cost 85.0] [--avg-task-hours 4.0]
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import OUTPUT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("calculate_metrics")


def load_json(filename: str) -> dict | list | None:
    """Carrega um arquivo JSON do diretório de saída."""
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"Arquivo não encontrado: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Dados salvos em {path}")


# ─── Camada A: Score de Adoção ─────────────────────────────────────────────

def calculate_adoption_score(
    sessions_summary: dict,
    members_summary: dict,
    dau_data: list,
) -> dict:
    """
    Score de Adoção (0-100):
      - Amplitude: % de membros que usaram Devin no período
      - Intensidade: Média de sessões por usuário ativo
      - Recorrência: % de dias com pelo menos 1 usuário ativo (DAU > 0)
    """
    total_members = members_summary.get("total_membros", 1)
    unique_users = sessions_summary.get("usuarios_unicos", 0)
    total_sessions = sessions_summary.get("total_sessions", 0)

    # Amplitude (0-40 pontos)
    amplitude_pct = min(100, (unique_users / max(total_members, 1)) * 100)
    amplitude_score = (amplitude_pct / 100) * 40

    # Intensidade (0-30 pontos) — meta: 5+ sessões/usuário/mês
    sessions_per_user = total_sessions / max(unique_users, 1)
    intensity_score = min(30, (sessions_per_user / 5) * 30)

    # Recorrência (0-30 pontos) — % de dias com DAU > 0
    if dau_data and isinstance(dau_data, list):
        days_with_activity = sum(1 for d in dau_data if d.get("active_users", 0) > 0)
        total_days = max(len(dau_data), 1)
        recurrence_pct = (days_with_activity / total_days) * 100
    else:
        recurrence_pct = 0
    recurrence_score = (recurrence_pct / 100) * 30

    total_score = round(amplitude_score + intensity_score + recurrence_score, 1)

    return {
        "score_adocao": total_score,
        "max_score": 100,
        "componentes": {
            "amplitude": {
                "valor": round(amplitude_pct, 1),
                "unidade": "% de membros ativos",
                "score": round(amplitude_score, 1),
                "peso": 40,
            },
            "intensidade": {
                "valor": round(sessions_per_user, 1),
                "unidade": "sessões/usuário",
                "score": round(intensity_score, 1),
                "peso": 30,
            },
            "recorrencia": {
                "valor": round(recurrence_pct, 1),
                "unidade": "% de dias com atividade",
                "score": round(recurrence_score, 1),
                "peso": 30,
            },
        },
    }


# ─── Camada B: Score de Eficiência ─────────────────────────────────────────

def calculate_efficiency_score(sessions_summary: dict) -> dict:
    """
    Score de Eficiência (0-100):
      - Taxa de produtividade: % de sessões que geraram PRs mergeadas
      - Eficiência de ACU: ACUs por PR mergeada (quanto menor, melhor)
      - Taxa de merge: PRs mergeadas / PRs abertas
    """
    productivity_rate = sessions_summary.get("taxa_produtividade", 0)
    merge_rate = sessions_summary.get("taxa_merge", 0)
    acu_per_pr = sessions_summary.get("acu_por_pr_mergeada")

    # Produtividade (0-40 pontos) — meta: 50%+ de sessões produtivas
    prod_score = min(40, (productivity_rate / 50) * 40)

    # Taxa de merge (0-30 pontos) — meta: 70%+
    merge_score = min(30, (merge_rate / 70) * 30)

    # Eficiência de ACU (0-30 pontos) — meta: < 5 ACUs por PR mergeada
    if acu_per_pr is not None and acu_per_pr > 0:
        acu_efficiency = max(0, min(30, (1 - (acu_per_pr - 1) / 10) * 30))
    else:
        acu_efficiency = 0

    total_score = round(prod_score + merge_score + acu_efficiency, 1)

    return {
        "score_eficiencia": total_score,
        "max_score": 100,
        "componentes": {
            "taxa_produtividade": {
                "valor": round(productivity_rate, 1),
                "unidade": "%",
                "score": round(prod_score, 1),
                "peso": 40,
            },
            "taxa_merge": {
                "valor": round(merge_rate, 1),
                "unidade": "%",
                "score": round(merge_score, 1),
                "peso": 30,
            },
            "eficiencia_acu": {
                "valor": acu_per_pr,
                "unidade": "ACU/PR mergeada",
                "score": round(acu_efficiency, 1),
                "peso": 30,
            },
        },
    }


# ─── Camada E: Análise de ROI ──────────────────────────────────────────────

def calculate_roi(
    sessions_summary: dict,
    consumption_summary: dict,
    dev_hour_cost: float,
    avg_task_hours: float,
) -> dict:
    """
    Calcula ROI estimado do Devin Enterprise.

    Premissas configuráveis:
      - dev_hour_cost: Custo médio da hora de um desenvolvedor (R$ ou USD)
      - avg_task_hours: Horas médias que um dev levaria para fazer o que o Devin fez em 1 sessão produtiva

    Fórmulas:
      - Horas Economizadas = Sessões Produtivas × avg_task_hours
      - Custo Evitado = Horas Economizadas × dev_hour_cost
      - Custo Devin = Total ACUs × Custo por ACU (estimado)
      - ROI = (Custo Evitado - Custo Devin) / Custo Devin × 100
    """
    productive_sessions = sessions_summary.get("sessoes_produtivas", 0)
    total_acus = consumption_summary.get("total_acus_periodo", 0) if consumption_summary else 0

    # Horas economizadas
    hours_saved = productive_sessions * avg_task_hours
    cost_avoided = hours_saved * dev_hour_cost

    # Custo do Devin (estimativa: ~$1 por ACU como referência)
    # O usuário deve ajustar conforme seu contrato
    acu_unit_cost = float(os.environ.get("DEVIN_ACU_COST", "1.0"))
    devin_cost = total_acus * acu_unit_cost

    # ROI
    roi_pct = ((cost_avoided - devin_cost) / max(devin_cost, 1)) * 100 if devin_cost > 0 else 0

    # Payback (meses para o custo evitado cobrir o investimento)
    monthly_savings = cost_avoided  # Já é do período (default 30 dias)
    monthly_cost = devin_cost
    payback_months = monthly_cost / max(monthly_savings, 1) if monthly_savings > 0 else None

    # Custo por PR mergeada
    total_merged = sessions_summary.get("total_prs_mergeadas", 0)
    cost_per_merged_pr = devin_cost / max(total_merged, 1) if total_merged > 0 else None

    # Custo por hora economizada
    cost_per_hour_saved = devin_cost / max(hours_saved, 1) if hours_saved > 0 else None

    return {
        "premissas": {
            "custo_hora_desenvolvedor": dev_hour_cost,
            "horas_medias_por_tarefa": avg_task_hours,
            "custo_unitario_acu": acu_unit_cost,
        },
        "resultados": {
            "sessoes_produtivas": productive_sessions,
            "horas_economizadas": round(hours_saved, 1),
            "custo_evitado": round(cost_avoided, 2),
            "custo_devin_periodo": round(devin_cost, 2),
            "roi_percentual": round(roi_pct, 1),
            "payback_meses": round(payback_months, 2) if payback_months else None,
            "custo_por_pr_mergeada": round(cost_per_merged_pr, 2) if cost_per_merged_pr else None,
            "custo_por_hora_economizada": round(cost_per_hour_saved, 2) if cost_per_hour_saved else None,
        },
        "interpretacao": {
            "roi_positivo": roi_pct > 0,
            "nivel": (
                "Excelente" if roi_pct > 200
                else "Bom" if roi_pct > 100
                else "Moderado" if roi_pct > 0
                else "Negativo"
            ),
        },
    }


# ─── Score Consolidado de Maturidade ───────────────────────────────────────

def calculate_maturity_score(adoption: dict, efficiency: dict, roi: dict) -> dict:
    """
    Score Consolidado de Maturidade do Uso do Devin (0-100).

    Composição:
      - Adoção: 30%
      - Eficiência: 40%
      - ROI: 30%
    """
    adoption_score = adoption.get("score_adocao", 0)
    efficiency_score = efficiency.get("score_eficiencia", 0)

    # Normalizar ROI para score 0-100
    roi_pct = roi.get("resultados", {}).get("roi_percentual", 0)
    roi_score = min(100, max(0, roi_pct / 3))  # 300% ROI = score 100

    maturity = (
        adoption_score * 0.30
        + efficiency_score * 0.40
        + roi_score * 0.30
    )

    # Classificação
    if maturity >= 80:
        nivel = "Avançado"
        recomendacao = "Expandir uso para mais equipes e cenários complexos."
    elif maturity >= 60:
        nivel = "Intermediário"
        recomendacao = "Focar em aumentar taxa de merge e reduzir ACU por PR."
    elif maturity >= 40:
        nivel = "Inicial"
        recomendacao = "Investir em treinamento e playbooks para aumentar adoção."
    else:
        nivel = "Exploratório"
        recomendacao = "Definir casos de uso claros e criar baseline de métricas."

    return {
        "score_maturidade": round(maturity, 1),
        "max_score": 100,
        "nivel": nivel,
        "recomendacao": recomendacao,
        "composicao": {
            "adocao": {"score": round(adoption_score, 1), "peso": "30%"},
            "eficiencia": {"score": round(efficiency_score, 1), "peso": "40%"},
            "roi": {"score": round(roi_score, 1), "peso": "30%"},
        },
        "semaforo": (
            "verde" if maturity >= 70
            else "amarelo" if maturity >= 40
            else "vermelho"
        ),
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cálculo de métricas derivadas do Devin Enterprise")
    parser.add_argument("--dev-hour-cost", type=float, default=85.0,
                        help="Custo médio da hora de um desenvolvedor (default: 85.0)")
    parser.add_argument("--avg-task-hours", type=float, default=4.0,
                        help="Horas médias por tarefa que o Devin substitui (default: 4.0)")
    args = parser.parse_args()

    logger.info("Carregando dados extraídos...")

    sessions_summary = load_json("sessions_summary.json") or {}
    consumption_summary = load_json("consumption_summary.json") or {}
    members_summary = load_json("members_orgs_summary.json") or {}
    dau_data = load_json("active_users_dau.json") or []

    # Calcular scores
    logger.info("Calculando Score de Adoção...")
    adoption = calculate_adoption_score(sessions_summary, members_summary, dau_data)

    logger.info("Calculando Score de Eficiência...")
    efficiency = calculate_efficiency_score(sessions_summary)

    logger.info("Calculando ROI...")
    roi = calculate_roi(sessions_summary, consumption_summary, args.dev_hour_cost, args.avg_task_hours)

    logger.info("Calculando Score de Maturidade...")
    maturity = calculate_maturity_score(adoption, efficiency, roi)

    # Consolidar métricas derivadas
    derived = {
        "camada_a_adocao": adoption,
        "camada_b_eficiencia": efficiency,
        "camada_e_roi": roi,
        "maturidade_consolidada": maturity,
    }

    save_json(derived, "derived_metrics.json")
    save_json(roi, "roi_analysis.json")
    save_json(maturity, "maturity_scorecard.json")

    logger.info(f"Score de Maturidade: {maturity['score_maturidade']}/100 ({maturity['nivel']})")
    logger.info(f"ROI: {roi['resultados']['roi_percentual']}%")
    logger.info("Cálculo de métricas derivadas concluído.")


if __name__ == "__main__":
    main()
