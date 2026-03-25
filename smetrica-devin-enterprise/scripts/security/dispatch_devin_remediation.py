#!/usr/bin/env python3
"""
Dispatcher de Remediação — Cria sessões Devin Enterprise a partir de vulnerabilidades parseadas.

Lê o JSON gerado por parse_trivy_report.py ou parse_sysdig_report.py e cria
sessões programáticas no Devin Enterprise para remediar cada pacote vulnerável.

Modos de operação:
  - single: Uma sessão por pacote (granular, melhor rastreabilidade).
  - batch:  Uma sessão por repositório com todos os pacotes (menos ACU, menos PRs).

Funcionalidades:
  - Cria sessões via API do Devin Enterprise (v3)
  - Aplica Playbook de segurança (se configurado)
  - Define tags para rastreabilidade (security-remediation, severidade, pacote)
  - Define limite de ACU por sessão
  - Gera relatório de sessões criadas para tracking

Uso:
  export DEVIN_API_KEY="cog_..."
  python3 scripts/security/dispatch_devin_remediation.py \
    --input output/trivy_parsed.json \
    --mode batch \
    --repo-url https://github.com/org/repo \
    --playbook-id pb_security_123 \
    --max-acu 50 \
    --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("dispatch_remediation")


def load_parsed_report(input_path: str) -> dict:
    """Carrega o relatório parseado (Trivy ou Sysdig)."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_batch_prompt(prompts: list, repo_url: str = "") -> str:
    """
    Consolida múltiplos prompts de pacotes em um único prompt batch.
    Isso reduz o consumo de ACU e gera um único PR com todas as atualizações.
    """
    packages_summary = []
    for p in prompts:
        packages_summary.append(
            f"  - {p['package']}: atualizar para corrigir {p['vuln_count']} vulnerabilidade(s) "
            f"(severidade: {p['severity']})"
        )

    packages_text = "\n".join(packages_summary)

    batch_prompt = (
        f"REMEDIAÇÃO DE SEGURANÇA EM LOTE\n\n"
        f"Atualize as seguintes dependências vulneráveis neste repositório:\n\n"
        f"{packages_text}\n\n"
        f"Para cada pacote:\n"
        f"1. Atualize a versão no arquivo de manifesto correspondente "
        f"(package.json, requirements.txt, pom.xml, go.mod, Gemfile, etc.).\n"
        f"2. Verifique breaking changes no changelog de cada biblioteca.\n"
        f"3. Se houver breaking changes, atualize o código da aplicação.\n"
        f"4. Execute a suíte de testes unitários e de integração.\n"
        f"5. Se os testes passarem, abra um único PR consolidado com título:\n"
        f"   'fix(security): atualizar {len(prompts)} dependências vulneráveis'\n"
        f"6. No corpo do PR, liste cada pacote atualizado e as CVEs corrigidas.\n"
        f"7. Se algum pacote causar falha nos testes, documente no PR e prossiga "
        f"com os demais.\n"
    )

    if repo_url:
        batch_prompt += f"\nRepositório: {repo_url}\n"

    return batch_prompt


def dispatch_single_mode(client: DevinAPIClient, prompts: list,
                         playbook_id: str, max_acu: int, repo_url: str,
                         dry_run: bool) -> list:
    """Cria uma sessão Devin por pacote."""
    sessions = []

    for i, p in enumerate(prompts):
        logger.info(f"[{i+1}/{len(prompts)}] Pacote: {p['package']} ({p['severity']})")

        if dry_run:
            logger.info(f"  [DRY-RUN] Sessão seria criada com prompt de {len(p['prompt'])} chars")
            sessions.append({
                "package": p["package"],
                "severity": p["severity"],
                "status": "dry-run",
                "session_id": None,
            })
            continue

        payload = {
            "prompt": p["prompt"],
            "tags": p["tags"],
        }
        if playbook_id:
            payload["playbook_id"] = playbook_id
        if max_acu > 0:
            payload["max_acu"] = max_acu

        try:
            resp = client.post("/v3beta1/enterprise/sessions", json_data=payload)
            session_id = resp.get("session_id", resp.get("id", "unknown"))
            session_url = resp.get("url", f"https://app.devin.ai/sessions/{session_id}")

            logger.info(f"  Sessão criada: {session_id}")
            sessions.append({
                "package": p["package"],
                "severity": p["severity"],
                "status": "created",
                "session_id": session_id,
                "session_url": session_url,
            })

            # Rate limiting entre criações de sessão
            time.sleep(2)

        except Exception as e:
            logger.error(f"  Falha ao criar sessão: {e}")
            sessions.append({
                "package": p["package"],
                "severity": p["severity"],
                "status": "failed",
                "error": str(e),
            })

    return sessions


def dispatch_batch_mode(client: DevinAPIClient, prompts: list,
                        playbook_id: str, max_acu: int, repo_url: str,
                        dry_run: bool) -> list:
    """Cria uma única sessão Devin com todos os pacotes consolidados."""
    batch_prompt = create_batch_prompt(prompts, repo_url)

    # Tags consolidadas
    severities = set(p["severity"].lower() for p in prompts)
    tags = ["security-remediation", "batch-update"]
    for sev in severities:
        tags.append(f"severity-{sev}")

    logger.info(f"Modo batch: {len(prompts)} pacotes em 1 sessão")

    if dry_run:
        logger.info(f"[DRY-RUN] Sessão batch seria criada com prompt de {len(batch_prompt)} chars")
        return [{
            "mode": "batch",
            "packages": [p["package"] for p in prompts],
            "status": "dry-run",
            "session_id": None,
        }]

    payload = {
        "prompt": batch_prompt,
        "tags": tags,
    }
    if playbook_id:
        payload["playbook_id"] = playbook_id
    if max_acu > 0:
        payload["max_acu"] = max_acu

    try:
        resp = client.post("/v3beta1/enterprise/sessions", json_data=payload)
        session_id = resp.get("session_id", resp.get("id", "unknown"))
        session_url = resp.get("url", f"https://app.devin.ai/sessions/{session_id}")

        logger.info(f"Sessão batch criada: {session_id}")
        return [{
            "mode": "batch",
            "packages": [p["package"] for p in prompts],
            "status": "created",
            "session_id": session_id,
            "session_url": session_url,
        }]

    except Exception as e:
        logger.error(f"Falha ao criar sessão batch: {e}")
        return [{
            "mode": "batch",
            "packages": [p["package"] for p in prompts],
            "status": "failed",
            "error": str(e),
        }]


def filter_by_severity(prompts: list, min_severity: str) -> list:
    """Filtra prompts por severidade mínima."""
    severity_threshold = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    threshold = severity_threshold.get(min_severity.upper(), 3)

    filtered = [p for p in prompts if severity_threshold.get(p["severity"].upper(), 99) <= threshold]
    logger.info(f"Filtro de severidade >= {min_severity}: {len(filtered)}/{len(prompts)} prompts")
    return filtered


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dispatcher de remediação via Devin Enterprise")
    parser.add_argument("--input", "-i", required=True,
                        help="JSON gerado por parse_trivy_report.py ou parse_sysdig_report.py")
    parser.add_argument("--mode", choices=["single", "batch"], default="batch",
                        help="Modo: 'single' (1 sessão por pacote) ou 'batch' (1 sessão consolidada)")
    parser.add_argument("--repo-url", default="", help="URL do repositório Git")
    parser.add_argument("--playbook-id", default="", help="ID do Playbook de segurança no Devin")
    parser.add_argument("--max-acu", type=int, default=50, help="Limite de ACU por sessão")
    parser.add_argument("--min-severity", default="HIGH",
                        help="Severidade mínima para criar sessão (CRITICAL, HIGH, MEDIUM, LOW)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular sem criar sessões reais")
    parser.add_argument("--output", "-o", default="output/remediation_dispatch.json",
                        help="Caminho de saída do relatório de dispatch")
    args = parser.parse_args()

    # Carregar relatório parseado
    report = load_parsed_report(args.input)
    prompts = report.get("devin_prompts", [])

    if not prompts:
        logger.warning("Nenhum prompt de remediação encontrado no relatório.")
        return

    # Filtrar por severidade
    prompts = filter_by_severity(prompts, args.min_severity)
    if not prompts:
        logger.warning(f"Nenhum prompt com severidade >= {args.min_severity}.")
        return

    # Inicializar cliente Devin
    api_key = os.environ.get("DEVIN_API_KEY", "")
    if not api_key and not args.dry_run:
        logger.error("DEVIN_API_KEY não configurada.")
        sys.exit(1)

    client = DevinAPIClient(api_key) if api_key else None

    # Dispatch
    if args.mode == "single":
        sessions = dispatch_single_mode(
            client, prompts, args.playbook_id, args.max_acu, args.repo_url, args.dry_run
        )
    else:
        sessions = dispatch_batch_mode(
            client, prompts, args.playbook_id, args.max_acu, args.repo_url, args.dry_run
        )

    # Salvar relatório de dispatch
    output_dir = os.path.dirname(args.output) or "."
    os.makedirs(output_dir, exist_ok=True)

    dispatch_report = {
        "mode": args.mode,
        "min_severity": args.min_severity,
        "dry_run": args.dry_run,
        "total_prompts": len(prompts),
        "sessions": sessions,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dispatch_report, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Relatório de dispatch salvo em {args.output}")

    created = sum(1 for s in sessions if s["status"] == "created")
    failed = sum(1 for s in sessions if s["status"] == "failed")
    logger.info(f"Sessões: {created} criadas, {failed} falharam")


if __name__ == "__main__":
    main()
