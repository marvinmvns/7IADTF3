#!/usr/bin/env python3
"""
Métricas de Eficiência de Remediação — Mede o impacto do Devin na correção de vulnerabilidades.

Cruza os dados de sessões Devin (extraídos pela pipeline principal) com os dados
de vulnerabilidades (parseados do Sysdig/Trivy) para calcular métricas de eficiência.

Métricas calculadas:
  - MTTR (Mean Time to Remediate) via Devin vs baseline humano
  - Taxa de Remediação Autônoma (Auto-Fix Rate)
  - Custo por Vulnerabilidade Corrigida (ACU)
  - Horas de SecOps Economizadas
  - Redução de Backlog de Segurança
  - Taxa de Quebra (Breakage Rate)
  - Score de Eficiência de Segurança

Uso:
  python3 scripts/security/measure_remediation_efficiency.py \
    --sessions output/enterprise_sessions.json \
    --dispatch output/remediation_dispatch.json \
    --baseline-mttr-hours 48 \
    --dev-hour-cost 85.0 \
    --acu-cost 1.0
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("measure_remediation")


def load_json(path: str) -> dict:
    """Carrega um arquivo JSON."""
    if not os.path.exists(path):
        logger.warning(f"Arquivo não encontrado: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_security_sessions(sessions: list) -> list:
    """Filtra sessões que são de remediação de segurança (por tags)."""
    security_sessions = []
    for s in sessions:
        tags = s.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        if any("security" in t.lower() or "remediation" in t.lower() for t in tags):
            security_sessions.append(s)
    return security_sessions


def calculate_mttr(sessions: list) -> dict:
    """
    Calcula o Mean Time to Remediate (MTTR) baseado nas sessões Devin.
    MTTR = tempo médio desde a criação da sessão até o merge do PR.
    """
    remediation_times = []

    for s in sessions:
        created = s.get("created_at", "")
        # Tentar encontrar o timestamp de conclusão
        completed = s.get("completed_at", s.get("updated_at", ""))
        status = s.get("status", "")

        if not created or not completed:
            continue

        try:
            t_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            t_completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            delta_hours = (t_completed - t_created).total_seconds() / 3600
            if delta_hours > 0:
                remediation_times.append(delta_hours)
        except (ValueError, TypeError):
            continue

    if not remediation_times:
        return {"mttr_hours": None, "mttr_min": None, "mttr_max": None, "sample_size": 0}

    avg_mttr = sum(remediation_times) / len(remediation_times)
    return {
        "mttr_hours": round(avg_mttr, 2),
        "mttr_min": round(min(remediation_times), 2),
        "mttr_max": round(max(remediation_times), 2),
        "sample_size": len(remediation_times),
    }


def calculate_auto_fix_rate(sessions: list) -> dict:
    """
    Calcula a taxa de remediação autônoma.
    Auto-Fix Rate = sessões com PR mergeada / total de sessões de segurança.
    """
    total = len(sessions)
    if total == 0:
        return {"auto_fix_rate": 0, "total": 0, "merged": 0, "failed": 0}

    merged = 0
    failed = 0
    in_progress = 0

    for s in sessions:
        status = s.get("status", "").lower()
        pr_merged = s.get("pull_request_merged", False)

        if pr_merged or status in ("completed", "merged"):
            merged += 1
        elif status in ("failed", "error", "stopped"):
            failed += 1
        else:
            in_progress += 1

    return {
        "auto_fix_rate": round((merged / total) * 100, 1) if total > 0 else 0,
        "total": total,
        "merged": merged,
        "failed": failed,
        "in_progress": in_progress,
    }


def calculate_cost_per_fix(sessions: list, acu_cost: float) -> dict:
    """
    Calcula o custo por vulnerabilidade corrigida.
    Custo = (ACUs consumidos * custo por ACU) / PRs mergeadas.
    """
    total_acus = 0
    merged_count = 0

    for s in sessions:
        acus = s.get("total_acus", s.get("acu_used", 0)) or 0
        total_acus += acus

        status = s.get("status", "").lower()
        pr_merged = s.get("pull_request_merged", False)
        if pr_merged or status in ("completed", "merged"):
            merged_count += 1

    total_cost = total_acus * acu_cost
    cost_per_fix = total_cost / merged_count if merged_count > 0 else 0

    return {
        "total_acus": round(total_acus, 2),
        "total_cost": round(total_cost, 2),
        "merged_count": merged_count,
        "cost_per_fix": round(cost_per_fix, 2),
        "acu_cost_unit": acu_cost,
    }


def calculate_hours_saved(sessions: list, baseline_mttr_hours: float,
                          dev_hour_cost: float) -> dict:
    """
    Calcula as horas de SecOps economizadas.
    Horas economizadas = (MTTR humano - MTTR Devin) * número de correções.
    """
    mttr_data = calculate_mttr(sessions)
    devin_mttr = mttr_data.get("mttr_hours") or 0

    merged_count = sum(
        1 for s in sessions
        if s.get("pull_request_merged", False) or s.get("status", "").lower() in ("completed", "merged")
    )

    hours_saved_per_fix = max(0, baseline_mttr_hours - devin_mttr)
    total_hours_saved = hours_saved_per_fix * merged_count
    money_saved = total_hours_saved * dev_hour_cost

    return {
        "baseline_mttr_hours": baseline_mttr_hours,
        "devin_mttr_hours": devin_mttr,
        "hours_saved_per_fix": round(hours_saved_per_fix, 2),
        "total_fixes": merged_count,
        "total_hours_saved": round(total_hours_saved, 2),
        "money_saved": round(money_saved, 2),
        "dev_hour_cost": dev_hour_cost,
    }


def calculate_breakage_rate(sessions: list) -> dict:
    """
    Calcula a taxa de quebra: sessões onde o CI falhou após a atualização.
    """
    total = len(sessions)
    if total == 0:
        return {"breakage_rate": 0, "total": 0, "broken": 0}

    broken = sum(
        1 for s in sessions
        if s.get("status", "").lower() in ("failed", "error")
    )

    return {
        "breakage_rate": round((broken / total) * 100, 1),
        "total": total,
        "broken": broken,
    }


def calculate_security_efficiency_score(auto_fix_rate: float, breakage_rate: float,
                                         mttr_reduction_pct: float) -> dict:
    """
    Score consolidado de eficiência de segurança (0-100).
    Pesos: Auto-Fix Rate (40%), MTTR Reduction (40%), Baixa Quebra (20%).
    """
    # Normalizar breakage para score positivo (100 - breakage)
    breakage_score = max(0, 100 - breakage_rate)

    score = (
        auto_fix_rate * 0.40 +
        min(mttr_reduction_pct, 100) * 0.40 +
        breakage_score * 0.20
    )

    return {
        "security_efficiency_score": round(score, 1),
        "components": {
            "auto_fix_rate_weighted": round(auto_fix_rate * 0.40, 1),
            "mttr_reduction_weighted": round(min(mttr_reduction_pct, 100) * 0.40, 1),
            "low_breakage_weighted": round(breakage_score * 0.20, 1),
        }
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Métricas de eficiência de remediação")
    parser.add_argument("--sessions", default="output/enterprise_sessions.json",
                        help="JSON com sessões enterprise do Devin")
    parser.add_argument("--dispatch", default="output/remediation_dispatch.json",
                        help="JSON do relatório de dispatch")
    parser.add_argument("--baseline-mttr-hours", type=float, default=48.0,
                        help="MTTR humano baseline em horas (default: 48h)")
    parser.add_argument("--dev-hour-cost", type=float, default=85.0,
                        help="Custo da hora de um dev/SecOps (default: 85.0)")
    parser.add_argument("--acu-cost", type=float, default=1.0,
                        help="Custo por ACU (default: 1.0)")
    parser.add_argument("--output", "-o", default="output/remediation_efficiency.json",
                        help="Caminho de saída")
    args = parser.parse_args()

    # Carregar dados
    sessions_data = load_json(args.sessions)
    sessions_list = sessions_data if isinstance(sessions_data, list) else sessions_data.get("sessions", [])

    # Filtrar sessões de segurança
    security_sessions = filter_security_sessions(sessions_list)
    logger.info(f"Sessões de segurança encontradas: {len(security_sessions)}/{len(sessions_list)}")

    if not security_sessions:
        logger.warning("Nenhuma sessão de segurança encontrada. "
                       "Verifique se as sessões possuem tags 'security' ou 'remediation'.")
        # Gerar relatório vazio com instruções
        empty_report = {
            "status": "sem_dados",
            "instrucoes": (
                "Para gerar métricas, execute primeiro o dispatch_devin_remediation.py "
                "com tags de segurança, e depois extraia as sessões com extract_sessions.py."
            ),
        }
        output_dir = os.path.dirname(args.output) or "."
        os.makedirs(output_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(empty_report, f, indent=2, ensure_ascii=False)
        return

    # Calcular métricas
    mttr = calculate_mttr(security_sessions)
    auto_fix = calculate_auto_fix_rate(security_sessions)
    cost = calculate_cost_per_fix(security_sessions, args.acu_cost)
    hours = calculate_hours_saved(security_sessions, args.baseline_mttr_hours, args.dev_hour_cost)
    breakage = calculate_breakage_rate(security_sessions)

    # MTTR reduction percentage
    mttr_reduction_pct = 0
    if mttr["mttr_hours"] and args.baseline_mttr_hours > 0:
        mttr_reduction_pct = ((args.baseline_mttr_hours - mttr["mttr_hours"]) / args.baseline_mttr_hours) * 100

    score = calculate_security_efficiency_score(
        auto_fix["auto_fix_rate"],
        breakage["breakage_rate"],
        mttr_reduction_pct,
    )

    # Montar relatório final
    report = {
        "periodo": datetime.now().isoformat(),
        "total_sessoes_seguranca": len(security_sessions),
        "metricas": {
            "mttr": mttr,
            "auto_fix_rate": auto_fix,
            "custo_por_fix": cost,
            "horas_economizadas": hours,
            "taxa_de_quebra": breakage,
            "mttr_reduction_pct": round(mttr_reduction_pct, 1),
        },
        "score_consolidado": score,
        "roi_seguranca": {
            "investimento_devin": cost["total_cost"],
            "economia_gerada": hours["money_saved"],
            "roi_pct": round(
                ((hours["money_saved"] - cost["total_cost"]) / cost["total_cost"] * 100)
                if cost["total_cost"] > 0 else 0, 1
            ),
        },
    }

    # Salvar
    output_dir = os.path.dirname(args.output) or "."
    os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Relatório de eficiência salvo em {args.output}")
    logger.info(f"Score de Eficiência de Segurança: {score['security_efficiency_score']}/100")
    logger.info(f"Auto-Fix Rate: {auto_fix['auto_fix_rate']}%")
    logger.info(f"MTTR Devin: {mttr['mttr_hours']}h (baseline: {args.baseline_mttr_hours}h)")
    logger.info(f"ROI: {report['roi_seguranca']['roi_pct']}%")


if __name__ == "__main__":
    main()
