#!/bin/bash
# Download dos modelos GGUF para usar com llama.cpp SYCL (Intel Arc A770 / CPU)
set -e

MODEL_DIR="${1:-/models}"
mkdir -p "$MODEL_DIR"

# Modelo 1: Qwen 3.5 4B Q4_K_M (~2.6GB) - padrão com GPU
MODEL_FILE_1="$MODEL_DIR/Qwen3.5-4B-Q4_K_M.gguf"
if [ -f "$MODEL_FILE_1" ]; then
    echo "Modelo já existe: $MODEL_FILE_1"
else
    echo "Baixando Qwen 3.5 4B Q4_K_M (~2.6GB)..."
    curl -L -o "$MODEL_FILE_1" \
        "https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    echo "Modelo baixado: $MODEL_FILE_1"
    ls -lh "$MODEL_FILE_1"
fi

# Modelo 2: Qwen 3.5 9B Q4_K_M (~5.7GB) - modelo mais capaz da família Qwen 3.5
MODEL_FILE_2="$MODEL_DIR/Qwen3.5-9B-Q4_K_M.gguf"
if [ -f "$MODEL_FILE_2" ]; then
    echo "Modelo já existe: $MODEL_FILE_2"
else
    echo "Baixando Qwen 3.5 9B Q4_K_M (~5.7GB)..."
    curl -L -o "$MODEL_FILE_2" \
        "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf"
    echo "Modelo baixado: $MODEL_FILE_2"
    ls -lh "$MODEL_FILE_2"
fi

# Modelo 3: Qwen 2.5 3B Instruct Q4_K_M (~2GB) - alternativa CPU/XPU, cabe na A770 para treino
MODEL_FILE_2="$MODEL_DIR/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
if [ -f "$MODEL_FILE_2" ]; then
    echo "Modelo já existe: $MODEL_FILE_2"
else
    echo "Baixando Qwen 2.5 3B Instruct Q4_K_M (~2GB)..."
    curl -L -o "$MODEL_FILE_2" \
        "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    echo "Modelo baixado: $MODEL_FILE_2"
    ls -lh "$MODEL_FILE_2"
fi

# Modelo 3: LFM 2.5 1.2B Thinking Q4_K_M (~700MB) - Liquid AI, ultra-leve com reasoning
MODEL_FILE_3="$MODEL_DIR/LFM2.5-1.2B-Thinking-Q4_K_M.gguf"
if [ -f "$MODEL_FILE_3" ]; then
    echo "Modelo já existe: $MODEL_FILE_3"
else
    echo "Baixando LFM 2.5 1.2B Thinking Q4_K_M (~700MB)..."
    curl -L -o "$MODEL_FILE_3" \
        "https://huggingface.co/LiquidAI/LFM2.5-1.2B-Thinking-GGUF/resolve/main/LFM2.5-1.2B-Thinking-Q4_K_M.gguf"
    echo "Modelo baixado: $MODEL_FILE_3"
    ls -lh "$MODEL_FILE_3"
fi

echo ""
echo "=== Modelos disponíveis ==="
ls -lh "$MODEL_DIR"/*.gguf 2>/dev/null || echo "Nenhum modelo encontrado"
echo ""
echo "Todos os modelos prontos!"
