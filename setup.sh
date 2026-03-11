#!/bin/bash
# MedAssist - Script de Instalação e Setup
set -e

echo "============================================"
echo "  MedAssist - Assistente Médico Virtual"
echo "  Tech Challenge Fase 3 - FIAP"
echo "============================================"

# Verifica Docker
if ! command -v docker &> /dev/null; then
    echo "[ERRO] Docker não encontrado. Instale: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "[ERRO] Docker Compose não encontrado."
    exit 1
fi

# Cria .env se não existir
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "[INFO] Arquivo .env criado. Configure sua OPENAI_API_KEY."
fi

# Build e start
echo ""
echo "[1/3] Construindo imagens Docker..."
docker compose build

echo ""
echo "[2/3] Iniciando serviços..."
docker compose up -d

echo ""
echo "[3/3] Aguardando banco de dados..."
sleep 5

# Seed do banco
echo ""
echo "[INFO] Populando banco de dados com dados de exemplo..."
docker compose exec backend python scripts/seed_db.py || echo "[AVISO] Seed pode já ter sido executado."

echo ""
echo "============================================"
echo "  MedAssist está rodando!"
echo ""
echo "  Frontend: http://localhost"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Para usar Ollama (LLM local):"
echo "  docker compose --profile local-llm up -d"
echo "  docker compose exec ollama ollama pull llama3"
echo "============================================"
