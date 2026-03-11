FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl wget unzip \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright (para agente de navegação)
RUN pip install playwright && playwright install --with-deps chromium

# Cria diretórios para modelos TTS/STT
RUN mkdir -p /app/models/tts /app/models/stt

# Download modelo Vosk PT-BR (pequeno, ~50MB)
RUN wget -q https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip -O /tmp/vosk.zip \
    && unzip -q /tmp/vosk.zip -d /app/models/stt/ \
    && mv /app/models/stt/vosk-model-small-pt-0.3 /app/models/stt/vosk-model-pt-br \
    && rm /tmp/vosk.zip

# Download modelo Piper TTS PT-BR
RUN pip install piper-tts \
    && mkdir -p /app/models/tts \
    && wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx \
       -O /app/models/tts/pt_BR-faber-medium.onnx \
    && wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json \
       -O /app/models/tts/pt_BR-faber-medium.onnx.json \
    || echo "Piper models download skipped (optional)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
