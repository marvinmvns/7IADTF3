#!/usr/bin/env python3
"""
Parser de Relatórios Trivy SCA — Extrai e prioriza vulnerabilidades para remediação.

Lê a saída JSON do Trivy (gerada via `trivy image --format json -o report.json`)
e produz uma lista priorizada de vulnerabilidades que possuem correção disponível,
pronta para ser enviada ao Devin Enterprise.

Funcionalidades:
  - Parseia relatórios Trivy (image, fs, repo)
  - Filtra apenas vulnerabilidades com FixedVersion disponível
  - Prioriza por severidade (CRITICAL > HIGH > MEDIUM > LOW)
  - Agrupa por pacote para evitar duplicatas
  - Gera payload pronto para criação de sessão Devin

Uso:
  python3 scripts/security/parse_trivy_report.py --input trivy_report.json --output output/trivy_parsed.json

  # Gerar o relatório Trivy antes:
  trivy image --format json --output trivy_report.json minha-imagem:latest
  trivy fs --format json --output trivy_report.json ./meu-projeto
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("parse_trivy")

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def parse_trivy_json(report_path: str) -> list:
    """
    Parseia o JSON de saída do Trivy e retorna lista de vulnerabilidades
    com correção disponível, ordenadas por severidade.
    """
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    vulns = []

    # O Trivy pode retornar Results como lista de targets
    results = report.get("Results", [])
    if not results:
        logger.warning("Nenhum 'Results' encontrado no relatório Trivy.")
        return vulns

    for target in results:
        target_name = target.get("Target", "unknown")
        target_class = target.get("Class", "unknown")
        target_type = target.get("Type", "unknown")

        for vuln in target.get("Vulnerabilities", []):
            vuln_id = vuln.get("VulnerabilityID", "")
            pkg_name = vuln.get("PkgName", "")
            installed = vuln.get("InstalledVersion", "")
            fixed = vuln.get("FixedVersion", "")
            severity = vuln.get("Severity", "UNKNOWN")
            title = vuln.get("Title", "")
            description = vuln.get("Description", "")
            primary_url = vuln.get("PrimaryURL", "")

            # Só incluir se tem correção disponível
            if not fixed:
                continue

            vulns.append({
                "vuln_id": vuln_id,
                "package": pkg_name,
                "installed_version": installed,
                "fixed_version": fixed,
                "severity": severity,
                "severity_rank": SEVERITY_ORDER.get(severity, 99),
                "title": title,
                "description": description[:300],
                "url": primary_url,
                "target": target_name,
                "target_class": target_class,
                "target_type": target_type,
            })

    # Ordenar por severidade
    vulns.sort(key=lambda v: v["severity_rank"])
    logger.info(f"Total de vulnerabilidades com fix disponível: {len(vulns)}")
    return vulns


def group_by_package(vulns: list) -> dict:
    """
    Agrupa vulnerabilidades por pacote para evitar criar múltiplas sessões
    para o mesmo pacote. Cada pacote terá a versão mais alta de fix sugerida.
    """
    packages = defaultdict(lambda: {
        "package": "",
        "installed_version": "",
        "fixed_version": "",
        "max_severity": "LOW",
        "max_severity_rank": 99,
        "vuln_ids": [],
        "target": "",
        "target_type": "",
    })

    for v in vulns:
        key = f"{v['package']}@{v['target']}"
        pkg = packages[key]
        pkg["package"] = v["package"]
        pkg["installed_version"] = v["installed_version"]
        pkg["target"] = v["target"]
        pkg["target_type"] = v["target_type"]
        pkg["vuln_ids"].append(v["vuln_id"])

        # Manter a versão de fix mais alta
        if not pkg["fixed_version"] or v["fixed_version"] > pkg["fixed_version"]:
            pkg["fixed_version"] = v["fixed_version"]

        # Manter a severidade mais alta
        if v["severity_rank"] < pkg["max_severity_rank"]:
            pkg["max_severity"] = v["severity"]
            pkg["max_severity_rank"] = v["severity_rank"]

    result = sorted(packages.values(), key=lambda p: p["max_severity_rank"])
    logger.info(f"Pacotes únicos para atualização: {len(result)}")
    return result


def generate_devin_prompts(grouped_packages: list, repo_url: str = "") -> list:
    """
    Gera prompts prontos para criar sessões Devin de remediação.
    Cada prompt contém as instruções para atualizar um pacote específico.
    """
    prompts = []

    for pkg in grouped_packages:
        cve_list = ", ".join(pkg["vuln_ids"][:5])
        if len(pkg["vuln_ids"]) > 5:
            cve_list += f" (e mais {len(pkg['vuln_ids']) - 5})"

        prompt = (
            f"REMEDIAÇÃO DE SEGURANÇA — {pkg['max_severity']}\n\n"
            f"Atualize o pacote '{pkg['package']}' da versão {pkg['installed_version']} "
            f"para a versão {pkg['fixed_version']} (ou superior compatível).\n\n"
            f"Vulnerabilidades associadas: {cve_list}\n"
            f"Arquivo/Target: {pkg['target']}\n"
            f"Tipo: {pkg['target_type']}\n\n"
            f"Instruções:\n"
            f"1. Atualize a dependência no arquivo de manifesto correspondente "
            f"(package.json, requirements.txt, pom.xml, go.mod, etc.).\n"
            f"2. Verifique se há breaking changes documentadas no changelog da biblioteca.\n"
            f"3. Se houver breaking changes, atualize o código da aplicação.\n"
            f"4. Execute a suíte de testes unitários e de integração.\n"
            f"5. Se os testes passarem, abra um Pull Request com título: "
            f"'fix(security): atualizar {pkg['package']} para {pkg['fixed_version']} — {cve_list}'\n"
            f"6. Se os testes falharem, documente as falhas no PR como draft.\n"
        )

        if repo_url:
            prompt += f"\nRepositório: {repo_url}\n"

        prompts.append({
            "prompt": prompt,
            "tags": ["security-remediation", f"severity-{pkg['max_severity'].lower()}", pkg["package"]],
            "package": pkg["package"],
            "severity": pkg["max_severity"],
            "vuln_count": len(pkg["vuln_ids"]),
        })

    return prompts


def generate_summary(vulns: list, grouped: list) -> dict:
    """Gera resumo estatístico do relatório parseado."""
    severity_counts = defaultdict(int)
    for v in vulns:
        severity_counts[v["severity"]] += 1

    return {
        "total_vulnerabilidades_com_fix": len(vulns),
        "pacotes_unicos_para_atualizar": len(grouped),
        "por_severidade": dict(severity_counts),
        "estimativa_sessoes_devin": len(grouped),
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parser de relatórios Trivy para integração com Devin")
    parser.add_argument("--input", "-i", required=True, help="Caminho do relatório Trivy JSON")
    parser.add_argument("--output", "-o", default="output/trivy_parsed.json", help="Caminho de saída")
    parser.add_argument("--repo-url", default="", help="URL do repositório Git (opcional)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        logger.error(f"Arquivo não encontrado: {args.input}")
        sys.exit(1)

    # Parsear
    vulns = parse_trivy_json(args.input)
    if not vulns:
        logger.warning("Nenhuma vulnerabilidade com fix disponível encontrada.")
        return

    # Agrupar por pacote
    grouped = group_by_package(vulns)

    # Gerar prompts para Devin
    prompts = generate_devin_prompts(grouped, args.repo_url)

    # Resumo
    summary = generate_summary(vulns, grouped)

    # Salvar
    output_dir = os.path.dirname(args.output) or "."
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "summary": summary,
        "vulnerabilities": vulns,
        "grouped_packages": grouped,
        "devin_prompts": prompts,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Resultado salvo em {args.output}")
    logger.info(f"Resumo: {summary['total_vulnerabilidades_com_fix']} vulns, "
                f"{summary['pacotes_unicos_para_atualizar']} pacotes, "
                f"{summary['estimativa_sessoes_devin']} sessões Devin estimadas.")


if __name__ == "__main__":
    main()
