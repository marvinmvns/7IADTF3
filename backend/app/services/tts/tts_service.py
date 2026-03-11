"""Serviço TTS - Text-to-Speech com Piper (local, sem GPU)."""
import subprocess
import tempfile
import os
from app.config import get_settings


class TTSService:

    @staticmethod
    async def sintetizar(texto: str) -> bytes:
        """Converte texto em áudio WAV usando Piper TTS."""
        settings = get_settings()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        try:
            # Piper TTS - modelo local, CPU only
            cmd = [
                "piper",
                "--model", f"/app/models/tts/{settings.piper_voice}.onnx",
                "--output_file", output_path,
            ]
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            proc.communicate(input=texto.encode("utf-8"))

            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    return f.read()

            # Fallback: gerar silêncio se Piper não disponível
            return TTSService._gerar_silencio()
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @staticmethod
    def _gerar_silencio() -> bytes:
        """Gera arquivo WAV vazio como fallback."""
        import struct
        sample_rate = 22050
        duration = 1
        n_samples = sample_rate * duration
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + n_samples * 2, b'WAVE', b'fmt ', 16,
            1, 1, sample_rate, sample_rate * 2, 2, 16, b'data', n_samples * 2
        )
        return header + b'\x00' * (n_samples * 2)
