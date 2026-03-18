#!/bin/bash
# MedAssist - Script de Instalação e Setup
# Uso: ./setup.sh
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

# Cria .env se não existir
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "[INFO] Arquivo .env criado."
fi

# Baixa modelo GGUF se não existir
if [ ! -f models/Qwen3.5-4B-Q4_K_M.gguf ]; then
    echo "[INFO] Baixando modelo Qwen 3.5 4B (~2.6GB)..."
    mkdir -p models
    curl -L --progress-bar -o models/Qwen3.5-4B-Q4_K_M.gguf \
        "https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    echo "[INFO] Modelo baixado!"
fi

echo ""
echo "[1/3] Construindo imagens Docker..."
docker compose build

echo ""
echo "[2/3] Iniciando serviços..."
docker compose up -d

echo ""
echo "[3/3] Aguardando inicialização..."
echo "       llama-server demora ~3min no primeiro"
echo "       start (compilação de kernels SYCL)."
echo "       Starts subsequentes são mais rápidos."

echo ""
echo "============================================"
echo "  MedAssist iniciando!"
echo ""
echo "  Frontend:  http://localhost:8090"
echo "  Backend:   http://localhost:8001"
echo "  API Docs:  http://localhost:8001/docs"
echo "  LLM:       http://localhost:8081 (llama.cpp)"
echo ""
echo "  Seed, dataset e RAG carregam automaticamente."
echo "  Aguarde o llama-server ficar healthy antes"
echo "  de usar o chat (~3min primeira vez)."
echo "============================================"
