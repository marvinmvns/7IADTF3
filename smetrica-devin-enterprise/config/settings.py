"""
Configurações centrais para os scripts de extração das APIs Enterprise do Devin.

Variáveis de ambiente necessárias:
  DEVIN_API_KEY        -> Token de autenticação (cog_* para v3, apk_user_* para v2)
  DEVIN_ENTERPRISE_ID  -> ID da enterprise (opcional, usado em logs)
  DEVIN_ORG_IDS        -> IDs de organizações separados por vírgula (opcional)
  OUTPUT_DIR           -> Diretório de saída dos dados (padrão: ./output)
"""

import os
from datetime import datetime, timedelta, timezone

# ─── Autenticação ───────────────────────────────────────────────────────────
API_KEY = os.environ.get("DEVIN_API_KEY", "")
ENTERPRISE_ID = os.environ.get("DEVIN_ENTERPRISE_ID", "default")

# ─── Base URLs ──────────────────────────────────────────────────────────────
BASE_URL_V3 = "https://api.devin.ai/v3/enterprise"
BASE_URL_V3_BETA = "https://api.devin.ai/v3beta1/enterprise"
BASE_URL_V2 = "https://api.devin.ai/v2/enterprise"

# ─── Organizações (filtro opcional) ─────────────────────────────────────────
_org_ids_raw = os.environ.get("DEVIN_ORG_IDS", "")
ORG_IDS = [oid.strip() for oid in _org_ids_raw.split(",") if oid.strip()] or None

# ─── Período padrão de coleta ──────────────────────────────────────────────
# Por padrão, coleta os últimos 30 dias.
DEFAULT_DAYS_BACK = int(os.environ.get("DEVIN_DAYS_BACK", "30"))

_now = datetime.now(timezone.utc)
DEFAULT_END = _now
DEFAULT_START = _now - timedelta(days=DEFAULT_DAYS_BACK)

# Timestamps Unix (para endpoints v3 que usam epoch seconds)
DEFAULT_TIME_AFTER = int(DEFAULT_START.timestamp())
DEFAULT_TIME_BEFORE = int(DEFAULT_END.timestamp())

# ISO strings (para endpoints v2 que usam date-time)
DEFAULT_START_ISO = DEFAULT_START.strftime("%Y-%m-%dT%H:%M:%SZ")
DEFAULT_END_ISO = DEFAULT_END.strftime("%Y-%m-%dT%H:%M:%SZ")

# ─── Saída ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "output"))

# ─── Rate Limiting ──────────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = float(os.environ.get("DEVIN_REQUEST_DELAY", "0.5"))
MAX_RETRIES = int(os.environ.get("DEVIN_MAX_RETRIES", "3"))
RETRY_BACKOFF_FACTOR = float(os.environ.get("DEVIN_RETRY_BACKOFF", "2.0"))

# ─── Paginação ──────────────────────────────────────────────────────────────
DEFAULT_PAGE_LIMIT = int(os.environ.get("DEVIN_PAGE_LIMIT", "100"))
