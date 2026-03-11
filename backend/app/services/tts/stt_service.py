"""Serviço STT - Speech-to-Text com Vosk (local, sem GPU)."""
import json
import wave
import tempfile
import os


class STTService:

    MODEL_PATH = "/app/models/stt/vosk-model-pt-br"

    @staticmethod
    async def transcrever(audio_bytes: bytes) -> str:
        """Transcreve áudio para texto usando Vosk."""
        try:
            from vosk import Model, KaldiRecognizer

            # Salva áudio temporariamente
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                model = Model(STTService.MODEL_PATH)
                wf = wave.open(temp_path, "rb")
                rec = KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)

                texto_completo = []
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        texto_completo.append(result.get("text", ""))

                result = json.loads(rec.FinalResult())
                texto_completo.append(result.get("text", ""))
                wf.close()

                return " ".join(t for t in texto_completo if t).strip()
            finally:
                os.unlink(temp_path)

        except ImportError:
            return "[Vosk não instalado - instale com: pip install vosk]"
        except Exception as e:
            return f"[Erro na transcrição: {str(e)}]"
