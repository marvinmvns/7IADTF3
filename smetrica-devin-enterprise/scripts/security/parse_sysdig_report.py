#!/usr/bin/env python3
"""
Parser de Relatórios Sysdig Secure — Extrai vulnerabilidades para remediação via Devin.

Suporta dois modos de entrada:
  1. API: Consulta diretamente a API do Sysdig Secure para obter resultados de scan.
  2. Arquivo: Lê um JSON exportado manualmente do Sysdig Secure.

Funcionalidades:
  - Filtra vulnerabilidades com fix disponível (has_fix)
  - Prioriza por severidade + exploitability + contexto de runtime
  - Agrupa por pacote/imagem para batching eficiente
  - Gera payload pronto para criação de sessão Devin

Uso:
  # Via API do Sysdig
  export SYSDIG_API_TOKEN="seu_token"
  export SYSDIG_API_URL="https://api.us1.sysdig.com"
  python3 scripts/security/parse_sysdig_report.py --mode api --image-id sha256:abc123

  # Via arquivo JSON exportado
  python3 scripts/security/parse_sysdig_report.py --mode file --input sysdig_export.json
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

# Reutilizar o cliente HTTP do projeto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api_client import DevinAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("parse_sysdig")

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Negligible": 4, "Unknown": 5}


class SysdigClient:
    """Cliente simples para a API do Sysdig Secure."""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        import requests
        url = f"{self.api_url}{path}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def get_scan_results(self, image_id: str) -> dict:
        """Obtém resultados de scan de vulnerabilidades para uma imagem."""
        path = "/secure/vulnerability/v1beta1/results"
        params = {"imageId": image_id}
        return self._get(path, params)

    def get_runtime_results(self, limit: int = 100, cursor: str = "") -> dict:
        """Obtém resultados de vulnerabilidades em runtime."""
        path = "/secure/vulnerability/v1/runtime-results"
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get(path, params)

    def get_pipeline_results(self, limit: int = 100, cursor: str = "") -> dict:
        """Obtém resultados de vulnerabilidades de pipeline."""
        path = "/secure/vulnerability/v1/pipeline-results"
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get(path, params)


def parse_sysdig_results(data: dict) -> list:
    """
    Parseia a resposta da API do Sysdig e extrai vulnerabilidades
    com correção disponível.
    """
    vulns = []

    # A estrutura pode variar entre v1beta1 e v1
    # Tentar múltiplos caminhos
    packages = data.get("packages", data.get("result", {}).get("packages", []))
    if isinstance(packages, dict):
        packages = list(packages.values())

    for pkg in packages:
        pkg_name = pkg.get("name", pkg.get("packageName", ""))
        pkg_version = pkg.get("version", pkg.get("packageVersion", ""))
        pkg_type = pkg.get("type", pkg.get("packageType", ""))

        for vuln in pkg.get("vulns", pkg.get("vulnerabilities", [])):
            vuln_id = vuln.get("name", vuln.get("vulnId", vuln.get("id", "")))
            severity = vuln.get("severity", {})
            if isinstance(severity, dict):
                sev_label = severity.get("label", "Unknown")
            else:
                sev_label = str(severity)

            has_fix = vuln.get("fixedInVersion", vuln.get("fixVersion", ""))
            is_exploitable = vuln.get("exploitable", vuln.get("isExploitable", False))
            in_use = vuln.get("inUse", vuln.get("runtimeScope", False))

            if not has_fix:
                continue

            vulns.append({
                "vuln_id": vuln_id,
                "package": pkg_name,
                "installed_version": pkg_version,
                "fixed_version": str(has_fix),
                "severity": sev_label,
                "severity_rank": SEVERITY_ORDER.get(sev_label, 99),
                "package_type": pkg_type,
                "exploitable": bool(is_exploitable),
                "in_use_at_runtime": bool(in_use),
                "cvss_score": vuln.get("cvssScore", {}).get("value", {}).get("score", 0),
            })

    # Ordenar: exploitáveis em runtime primeiro, depois por severidade
    vulns.sort(key=lambda v: (
        0 if (v["exploitable"] and v["in_use_at_runtime"]) else 1,
        v["severity_rank"],
    ))

    logger.info(f"Total de vulnerabilidades com fix disponível: {len(vulns)}")
    return vulns


def parse_sysdig_file(file_path: str) -> list:
    """Parseia um arquivo JSON exportado do Sysdig."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_sysdig_results(data)


def group_by_package(vulns: list) -> list:
    """Agrupa vulnerabilidades por pacote para batching eficiente."""
    packages = defaultdict(lambda: {
        "package": "",
        "installed_version": "",
        "fixed_version": "",
        "max_severity": "Low",
        "max_severity_rank": 99,
        "vuln_ids": [],
        "package_type": "",
        "has_exploitable": False,
        "has_runtime": False,
    })

    for v in vulns:
        key = v["package"]
        pkg = packages[key]
        pkg["package"] = v["package"]
        pkg["installed_version"] = v["installed_version"]
        pkg["package_type"] = v["package_type"]
        pkg["vuln_ids"].append(v["vuln_id"])

        if not pkg["fixed_version"] or v["fixed_version"] > pkg["fixed_version"]:
            pkg["fixed_version"] = v["fixed_version"]

        if v["severity_rank"] < pkg["max_severity_rank"]:
            pkg["max_severity"] = v["severity"]
            pkg["max_severity_rank"] = v["severity_rank"]

        if v["exploitable"]:
            pkg["has_exploitable"] = True
        if v["in_use_at_runtime"]:
            pkg["has_runtime"] = True

    result = sorted(packages.values(), key=lambda p: (
        0 if (p["has_exploitable"] and p["has_runtime"]) else 1,
        p["max_severity_rank"],
    ))
    logger.info(f"Pacotes únicos para atualização: {len(result)}")
    return result


def generate_devin_prompts(grouped_packages: list, repo_url: str = "") -> list:
    """Gera prompts prontos para criar sessões Devin de remediação."""
    prompts = []

    for pkg in grouped_packages:
        cve_list = ", ".join(pkg["vuln_ids"][:5])
        if len(pkg["vuln_ids"]) > 5:
            cve_list += f" (e mais {len(pkg['vuln_ids']) - 5})"

        priority_tag = "URGENTE" if (pkg["has_exploitable"] and pkg["has_runtime"]) else pkg["max_severity"]

        prompt = (
            f"REMEDIAÇÃO DE SEGURANÇA — {priority_tag}\n\n"
            f"Atualize o pacote '{pkg['package']}' da versão {pkg['installed_version']} "
            f"para a versão {pkg['fixed_version']} (ou superior compatível).\n\n"
            f"Vulnerabilidades associadas: {cve_list}\n"
            f"Tipo de pacote: {pkg['package_type']}\n"
        )

        if pkg["has_exploitable"]:
            prompt += "ATENÇÃO: Vulnerabilidade com exploit conhecido.\n"
        if pkg["has_runtime"]:
            prompt += "ATENÇÃO: Pacote em uso ativo no runtime (detectado pelo Sysdig).\n"

        prompt += (
            f"\nInstruções:\n"
            f"1. Atualize a dependência no arquivo de manifesto correspondente.\n"
            f"2. Verifique breaking changes no changelog da biblioteca.\n"
            f"3. Se houver breaking changes, atualize o código da aplicação.\n"
            f"4. Execute a suíte de testes.\n"
            f"5. Se os testes passarem, abra um PR com título: "
            f"'fix(security): atualizar {pkg['package']} para {pkg['fixed_version']} — {cve_list}'\n"
            f"6. Se os testes falharem, documente as falhas no PR como draft.\n"
        )

        if repo_url:
            prompt += f"\nRepositório: {repo_url}\n"

        tags = ["security-remediation", f"severity-{pkg['max_severity'].lower()}", pkg["package"]]
        if pkg["has_exploitable"]:
            tags.append("exploitable")
        if pkg["has_runtime"]:
            tags.append("runtime-active")

        prompts.append({
            "prompt": prompt,
            "tags": tags,
            "package": pkg["package"],
            "severity": pkg["max_severity"],
            "vuln_count": len(pkg["vuln_ids"]),
            "exploitable": pkg["has_exploitable"],
            "runtime_active": pkg["has_runtime"],
        })

    return prompts


def generate_summary(vulns: list, grouped: list) -> dict:
    """Gera resumo estatístico."""
    severity_counts = defaultdict(int)
    exploitable_count = 0
    runtime_count = 0

    for v in vulns:
        severity_counts[v["severity"]] += 1
        if v["exploitable"]:
            exploitable_count += 1
        if v["in_use_at_runtime"]:
            runtime_count += 1

    return {
        "total_vulnerabilidades_com_fix": len(vulns),
        "pacotes_unicos_para_atualizar": len(grouped),
        "por_severidade": dict(severity_counts),
        "exploitaveis": exploitable_count,
        "em_uso_no_runtime": runtime_count,
        "estimativa_sessoes_devin": len(grouped),
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parser de relatórios Sysdig para integração com Devin")
    parser.add_argument("--mode", choices=["api", "file"], required=True,
                        help="Modo de entrada: 'api' para consultar Sysdig ou 'file' para ler JSON")
    parser.add_argument("--input", "-i", help="Caminho do JSON exportado (modo file)")
    parser.add_argument("--image-id", help="ID da imagem para consultar (modo api)")
    parser.add_argument("--output", "-o", default="output/sysdig_parsed.json", help="Caminho de saída")
    parser.add_argument("--repo-url", default="", help="URL do repositório Git (opcional)")
    args = parser.parse_args()

    vulns = []

    if args.mode == "api":
        api_url = os.environ.get("SYSDIG_API_URL", "")
        api_token = os.environ.get("SYSDIG_API_TOKEN", "")
        if not api_url or not api_token:
            logger.error("SYSDIG_API_URL e SYSDIG_API_TOKEN devem estar configurados.")
            sys.exit(1)
        if not args.image_id:
            logger.error("--image-id é obrigatório no modo api.")
            sys.exit(1)

        client = SysdigClient(api_url, api_token)
        data = client.get_scan_results(args.image_id)
        vulns = parse_sysdig_results(data)

    elif args.mode == "file":
        if not args.input or not os.path.exists(args.input):
            logger.error(f"Arquivo não encontrado: {args.input}")
            sys.exit(1)
        vulns = parse_sysdig_file(args.input)

    if not vulns:
        logger.warning("Nenhuma vulnerabilidade com fix disponível encontrada.")
        return

    grouped = group_by_package(vulns)
    prompts = generate_devin_prompts(grouped, args.repo_url)
    summary = generate_summary(vulns, grouped)

    output_dir = os.path.dirname(args.output) or "."
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "source": "sysdig",
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
