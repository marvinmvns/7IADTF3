"""Serviço STT - Speech-to-Text com Vosk (local, sem GPU)."""
import json
import subprocess
import wave
import tempfile
import os


class STTService:

    MODEL_PATH = "/opt/models/stt/vosk-model-pt-br"

    @staticmethod
    def _converter_para_wav(input_path: str) -> str:
        """Converte qualquer formato de áudio para WAV PCM 16kHz mono usando ffmpeg."""
        output_path = input_path + ".converted.wav"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1",
             "-f", "wav", "-acodec", "pcm_s16le", output_path],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou: {result.stderr.decode()[-200:]}")
        return output_path

    @staticmethod
    async def transcrever(audio_bytes: bytes) -> str:
        """Transcreve áudio para texto usando Vosk."""
        try:
            from vosk import Model, KaldiRecognizer

            # Salva áudio temporariamente
            is_wav = audio_bytes[:4] == b'RIFF'
            suffix = ".wav" if is_wav else ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            wav_path = temp_path
            try:
                # Converte para WAV se não for WAV nativo
                if not is_wav:
                    wav_path = STTService._converter_para_wav(temp_path)

                model = Model(STTService.MODEL_PATH)
                wf = wave.open(wav_path, "rb")
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
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                if wav_path != temp_path and os.path.exists(wav_path):
                    os.unlink(wav_path)

        except ImportError:
            return "[Vosk não instalado - instale com: pip install vosk]"
        except Exception as e:
            return f"[Erro na transcrição: {str(e)}]"
