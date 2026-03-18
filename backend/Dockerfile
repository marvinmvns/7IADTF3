# Base Intel com PyTorch XPU + Level Zero + oneAPI (Ubuntu 22.04, Python 3.10)
FROM intel/intel-extension-for-pytorch:2.8.10-xpu

WORKDIR /app

# Dependências do sistema + Docker CLI (para gerenciar llama-server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl wget unzip ffmpeg git ca-certificates gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala transformers do git (suporte a Qwen3.5 / qwen3_5 architecture)
RUN pip install --no-cache-dir --upgrade git+https://github.com/huggingface/transformers.git

# Instala Playwright (para agente de navegação)
RUN pip install playwright \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       fonts-unifont libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
       libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
       libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && playwright install chromium \
    && rm -rf /var/lib/apt/lists/*

# Download modelos TTS/STT para /opt/models (fora do /app para não ser sobrescrito pelo volume)
RUN mkdir -p /opt/models/tts /opt/models/stt

# Download modelo Vosk PT-BR (pequeno, ~50MB)
RUN wget -q https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip -O /tmp/vosk.zip \
    && unzip -q /tmp/vosk.zip -d /opt/models/stt/ \
    && mv /opt/models/stt/vosk-model-small-pt-0.3 /opt/models/stt/vosk-model-pt-br \
    && rm /tmp/vosk.zip

# Download modelo Piper TTS PT-BR
RUN pip install piper-tts \
    && wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx \
       -O /opt/models/tts/pt_BR-faber-medium.onnx \
    && wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json \
       -O /opt/models/tts/pt_BR-faber-medium.onnx.json \
    || echo "Piper models download skipped (optional)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
