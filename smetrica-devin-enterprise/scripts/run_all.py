#!/usr/bin/env python3
"""
Script Orquestrador — Executa toda a pipeline de extração e cálculo de métricas.

Ordem de execução:
  1. extract_members_orgs.py    → Dimensões (orgs, membros)
  2. extract_usage_metrics.py   → Métricas de uso (DAU/WAU/MAU, PRs, sessões)
  3. extract_sessions.py        → Sessões detalhadas
  4. extract_consumption.py     → Consumo e billing (ACUs)
  5. extract_audit_logs.py      → Audit logs (governança)
  6. calculate_metrics.py       → Métricas derivadas, ROI, scorecard

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/run_all.py [--dev-hour-cost 85.0] [--avg-task-hours 4.0] [--skip-audit]
"""

import argparse
import logging
import subprocess
import sys
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("run_all")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPTS_DIR)


def run_script(script_name: str, extra_args: list = None) -> bool:
    """Executa um script Python e retorna True se bem-sucedido."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path] + (extra_args or [])

    logger.info(f"{'='*60}")
    logger.info(f"Executando: {script_name}")
    logger.info(f"{'='*60}")

    start = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    elapsed = round(time.time() - start, 1)

    if result.returncode == 0:
        logger.info(f"{script_name} concluído em {elapsed}s")
        return True
    else:
        logger.error(f"{script_name} falhou (código {result.returncode}) após {elapsed}s")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pipeline completa de extração Devin Enterprise")
    parser.add_argument("--dev-hour-cost", type=float, default=85.0)
    parser.add_argument("--avg-task-hours", type=float, default=4.0)
    parser.add_argument("--skip-audit", action="store_true",
                        help="Pular extração de audit logs (mais rápido)")
    args = parser.parse_args()

    # Verificar API key
    if not os.environ.get("DEVIN_API_KEY"):
        logger.error("DEVIN_API_KEY não configurada. Exporte a variável de ambiente.")
        sys.exit(1)

    logger.info("Iniciando pipeline completa de extração Devin Enterprise")
    logger.info(f"Diretório do projeto: {PROJECT_DIR}")

    results = {}
    pipeline_start = time.time()

    # Etapa 1: Dimensões
    results["members_orgs"] = run_script("extract_members_orgs.py")

    # Etapa 2: Métricas de uso
    results["usage_metrics"] = run_script("extract_usage_metrics.py")

    # Etapa 3: Sessões detalhadas
    results["sessions"] = run_script("extract_sessions.py")

    # Etapa 4: Consumo
    results["consumption"] = run_script("extract_consumption.py")

    # Etapa 5: Audit logs (opcional)
    if not args.skip_audit:
        results["audit_logs"] = run_script("extract_audit_logs.py")
    else:
        logger.info("Audit logs pulados (--skip-audit)")
        results["audit_logs"] = "skipped"

    # Etapa 6: Métricas derivadas
    calc_args = [
        "--dev-hour-cost", str(args.dev_hour_cost),
        "--avg-task-hours", str(args.avg_task_hours),
    ]
    results["calculate_metrics"] = run_script("calculate_metrics.py", calc_args)

    # Resumo da execução
    total_time = round(time.time() - pipeline_start, 1)
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE CONCLUÍDA em {total_time}s")
    logger.info(f"{'='*60}")

    for script, status in results.items():
        icon = "OK" if status is True else ("SKIP" if status == "skipped" else "FALHA")
        logger.info(f"  [{icon}] {script}")

    failed = [k for k, v in results.items() if v is False]
    if failed:
        logger.warning(f"\nScripts com falha: {', '.join(failed)}")
        logger.warning("Verifique os logs acima para detalhes.")
        sys.exit(1)
    else:
        logger.info("\nTodos os scripts executados com sucesso.")
        logger.info(f"Dados disponíveis em: {os.path.join(PROJECT_DIR, 'output')}/")


if __name__ == "__main__":
    main()
