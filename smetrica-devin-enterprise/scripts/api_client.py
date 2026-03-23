"""
Cliente HTTP base para as APIs do Devin Enterprise.

Responsabilidades:
  - Autenticação via Bearer token
  - Retry com backoff exponencial
  - Rate limiting entre requisições
  - Paginação automática (cursor-based para v3, offset para v2)
  - Logging estruturado
"""

import time
import logging
import requests
from typing import Any

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    API_KEY,
    REQUEST_DELAY_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    DEFAULT_PAGE_LIMIT,
)

logger = logging.getLogger("devin_api")


class DevinAPIClient:
    """Cliente genérico para chamadas à API do Devin Enterprise."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError(
                "DEVIN_API_KEY não configurada. "
                "Exporte a variável de ambiente antes de executar."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ── Requisição com retry ────────────────────────────────────────────────
    def _request(self, method: str, url: str, params: dict = None, json_body: dict = None) -> dict:
        """Executa uma requisição HTTP com retry e backoff."""
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(REQUEST_DELAY_SECONDS)
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    timeout=30,
                )

                if resp.status_code == 429:
                    wait = RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"Rate limit (429). Aguardando {wait}s (tentativa {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.error(f"HTTP {resp.status_code} em {url}: {resp.text[:300]}")
                if resp.status_code in (401, 403):
                    raise  # Não faz sentido retry em erro de autenticação
                wait = RETRY_BACKOFF_FACTOR ** attempt
                logger.info(f"Retry em {wait}s (tentativa {attempt}/{MAX_RETRIES})")
                time.sleep(wait)

            except requests.exceptions.RequestException as e:
                last_error = e
                wait = RETRY_BACKOFF_FACTOR ** attempt
                logger.error(f"Erro de conexão: {e}. Retry em {wait}s")
                time.sleep(wait)

        raise RuntimeError(f"Falha após {MAX_RETRIES} tentativas: {last_error}")

    def get(self, url: str, params: dict = None) -> dict:
        return self._request("GET", url, params=params)

    # ── Paginação cursor-based (v3) ─────────────────────────────────────────
    def get_all_pages_cursor(self, url: str, params: dict = None, limit: int = None) -> list:
        """
        Itera sobre todas as páginas de um endpoint v3 que usa cursor-based pagination.
        Retorna a lista consolidada de items.
        """
        params = dict(params or {})
        params.setdefault("limit", limit or DEFAULT_PAGE_LIMIT)
        all_items = []

        while True:
            data = self.get(url, params=params)
            items = data.get("items", [])
            all_items.extend(items)

            if not data.get("has_next_page", False):
                break

            cursor = data.get("end_cursor")
            if not cursor:
                break
            params["cursor"] = cursor

            logger.info(f"Paginando... {len(all_items)} itens coletados até agora.")

        logger.info(f"Coleta finalizada: {len(all_items)} itens totais de {url}")
        return all_items

    # ── Paginação offset-based (v2) ─────────────────────────────────────────
    def get_all_pages_offset(self, url: str, params: dict = None, limit: int = None) -> list:
        """
        Itera sobre todas as páginas de um endpoint v2 que usa offset/limit.
        Retorna a lista consolidada.
        """
        params = dict(params or {})
        page_limit = limit or DEFAULT_PAGE_LIMIT
        params.setdefault("limit", page_limit)
        params.setdefault("offset", 0)
        all_items = []

        while True:
            data = self.get(url, params=params)

            # v2 pode retornar lista direta ou dict com chave específica
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Tenta encontrar a chave principal da lista
                for key in ("items", "sessions", "audit_logs", "members", "organizations"):
                    if key in data:
                        items = data[key]
                        break
                else:
                    items = [data]
            else:
                break

            all_items.extend(items)

            if len(items) < page_limit:
                break

            params["offset"] = params.get("offset", 0) + page_limit
            logger.info(f"Paginando... {len(all_items)} itens coletados até agora.")

        logger.info(f"Coleta finalizada: {len(all_items)} itens totais de {url}")
        return all_items
