"""Controller de Configuração - parametrização de LLM e TTS."""
import asyncio
import os
from pathlib import Path
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import ConfigLLMUpdate, ConfigLLMOut
from app.services.config_service import ConfigService
from app.config import get_settings
from app.utils.logger import registrar_log

router = APIRouter(prefix="/config", tags=["Configuração"])

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))


async def _docker_cmd(cmd: str) -> tuple[int, str]:
    """Executa comando docker e retorna (returncode, output)."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = (stdout or stderr or b"").decode().strip()
    return proc.returncode, output


async def _find_container(name_filter: str) -> str | None:
    """Encontra o nome real do container pelo filtro."""
    rc, output = await _docker_cmd(
        f"docker ps -a --filter name={name_filter} --format '{{{{.Names}}}}'"
    )
    if rc == 0 and output:
        # Pega o primeiro match que contém o filtro
        for line in output.split("\n"):
            if name_filter in line:
                return line.strip()
        return output.split("\n")[0].strip()
    return None


# ============ LLM Config ============

@router.get("/llm", response_model=ConfigLLMOut | None)
async def obter_config(db: AsyncSession = Depends(get_db)):
    return await ConfigService.obter_ativa(db)


@router.post("/llm", response_model=ConfigLLMOut)
async def salvar_config(dados: ConfigLLMUpdate, db: AsyncSession = Depends(get_db)):
    config = await ConfigService.salvar(db, dados)
    await registrar_log(db, "config_atualizada", f"Provider: {dados.provider}, Model: {dados.model_name}")
    return config


@router.get("/llm/historico", response_model=list[ConfigLLMOut])
async def historico_configs(db: AsyncSession = Depends(get_db)):
    return await ConfigService.listar(db)


# ============ llama-server (servidor único) ============

@router.get("/llama-server/status")
async def status_llama_server():
    """Retorna status do llama-server e modelo ativo."""
    settings = get_settings()

    # Modelo ativo (lê o symlink)
    symlink = MODELS_DIR / "active-model.gguf"
    modelo_ativo = None
    if symlink.is_symlink():
        modelo_ativo = os.readlink(str(symlink))
    elif symlink.exists():
        modelo_ativo = "active-model.gguf"

    # Status do servidor
    server_running = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.llama_cpp_url}/health")
            data = resp.json()
            server_running = data.get("status") == "ok"
    except Exception:
        pass

    # Lista modelos GGUF disponíveis
    modelos_disponiveis = []
    if MODELS_DIR.exists():
        for f in sorted(MODELS_DIR.glob("*.gguf")):
            if f.name == "active-model.gguf":
                continue
            modelos_disponiveis.append({
                "filename": f.name,
                "size_gb": round(f.stat().st_size / 1024**3, 1),
                "ativo": f.name == modelo_ativo,
            })

    return {
        "running": server_running,
        "modelo_ativo": modelo_ativo,
        "modelos_disponiveis": modelos_disponiveis,
    }


@router.post("/llama-server/trocar-modelo")
async def trocar_modelo(modelo: str, db: AsyncSession = Depends(get_db)):
    """Troca o modelo ativo: atualiza symlink e reinicia o llama-server."""
    model_path = MODELS_DIR / modelo
    if not model_path.exists():
        return {"sucesso": False, "erro": f"Modelo '{modelo}' não encontrado em {MODELS_DIR}"}

    symlink = MODELS_DIR / "active-model.gguf"

    # Atualiza symlink
    if symlink.exists() or symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(modelo)

    # Reinicia o llama-server
    container = await _find_container("llama-server")
    if container:
        await _docker_cmd(f"docker restart {container}")
        await registrar_log(db, "modelo_trocado", f"Modelo ativo: {modelo}")
        return {"sucesso": True, "modelo": modelo, "msg": f"Modelo trocado para {modelo}. Servidor reiniciando..."}

    return {"sucesso": True, "modelo": modelo, "msg": f"Symlink atualizado para {modelo}, mas container não encontrado para reiniciar."}


@router.post("/llama-server/stop")
async def parar_llama_server(db: AsyncSession = Depends(get_db)):
    """Para o llama-server para liberar VRAM da GPU."""
    container = await _find_container("llama-server")
    if not container:
        return {"sucesso": False, "erro": "Container llama-server não encontrado"}

    rc, output = await _docker_cmd(f"docker stop {container}")
    if rc == 0:
        await registrar_log(db, "llama_server_parado", "llama-server parado para liberar GPU")
        return {"sucesso": True, "msg": "llama-server parado"}
    return {"sucesso": False, "erro": output}


@router.post("/llama-server/start")
async def iniciar_llama_server(db: AsyncSession = Depends(get_db)):
    """Inicia o llama-server."""
    container = await _find_container("llama-server")
    if not container:
        return {"sucesso": False, "erro": "Container llama-server não encontrado"}

    rc, output = await _docker_cmd(f"docker start {container}")
    if rc == 0:
        await registrar_log(db, "llama_server_iniciado", "llama-server iniciado")
        return {"sucesso": True, "msg": "llama-server iniciado"}
    return {"sucesso": False, "erro": output}


# ============ GPU Info ============

@router.get("/gpu/info")
async def gpu_info():
    """Retorna informações da GPU (Intel Arc) e uso de VRAM."""
    try:
        import torch
        if not (hasattr(torch, "xpu") and torch.xpu.is_available()):
            return {"disponivel": False, "msg": "Intel XPU não disponível"}

        gpu_name = torch.xpu.get_device_name(0)
        total = torch.xpu.get_device_properties(0).total_memory
        # memory_allocated só rastreia PyTorch, não processos externos (llama-server)
        # Usa intel_gpu_top ou sysfs para uso real
        usado_pytorch = torch.xpu.memory_allocated(0)

        # Tenta ler uso real via sysfs (Intel i915/xe)
        usado_real = None
        try:
            # Verifica se llama-server está rodando (consome VRAM)
            container = await _find_container("llama-server")
            if container:
                rc, output = await _docker_cmd(f"docker inspect --format '{{{{.State.Running}}}}' {container}")
                llama_running = output.strip() == "true"
            else:
                llama_running = False

            if llama_running:
                # Estima VRAM usada pelo llama-server baseado no modelo ativo
                symlink = MODELS_DIR / "active-model.gguf"
                if symlink.is_symlink():
                    modelo_path = MODELS_DIR / os.readlink(str(symlink))
                    if modelo_path.exists():
                        usado_real = modelo_path.stat().st_size  # modelo ~= VRAM usada
        except Exception:
            pass

        total_gb = total / 1024**3
        usado_gb = (usado_real or usado_pytorch) / 1024**3
        livre_gb = total_gb - usado_gb

        return {
            "disponivel": True,
            "gpu_name": gpu_name,
            "vram_total_gb": round(total_gb, 1),
            "vram_usada_gb": round(usado_gb, 1),
            "vram_livre_gb": round(livre_gb, 1),
            "llama_server_rodando": usado_real is not None,
        }
    except Exception as e:
        return {"disponivel": False, "msg": str(e)}


# ============ Modelos disponíveis por provider ============

@router.get("/llama-cpp/modelos")
async def listar_modelos_llama_cpp(db: AsyncSession = Depends(get_db)):
    """Lista modelos GGUF disponíveis e o modelo carregado no servidor."""
    settings = get_settings()

    # Modelo carregado no servidor (resolve symlink para nome real)
    modelo_carregado = None
    server_online = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.llama_cpp_url}/v1/models")
            data = resp.json()
            for m in data.get("data", []):
                model_id = m.get("id", "unknown")
                # Se o servidor carregou o symlink, resolve para o nome real
                if model_id == "active-model.gguf":
                    symlink = MODELS_DIR / "active-model.gguf"
                    if symlink.is_symlink():
                        modelo_carregado = os.readlink(str(symlink))
                    else:
                        modelo_carregado = model_id
                else:
                    modelo_carregado = model_id
            server_online = True
    except Exception:
        pass

    # Lista todos os .gguf no diretório de modelos
    modelos = []
    if MODELS_DIR.exists():
        for f in sorted(MODELS_DIR.glob("*.gguf")):
            if f.name == "active-model.gguf":
                continue
            modelos.append({
                "name": f.name,
                "owned_by": "llamacpp",
                "size_gb": round(f.stat().st_size / 1024**3, 1),
                "ativo": f.name == modelo_carregado,
                "base_url": settings.llama_cpp_url,
            })

    status = "online" if server_online else "offline"
    return {"status": status, "modelos": modelos, "modelo_carregado": modelo_carregado}


@router.get("/ollama/modelos")
async def listar_modelos_ollama():
    """Lista modelos disponíveis no Ollama local."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            data = resp.json()
            modelos = []
            for m in data.get("models", []):
                modelos.append({
                    "name": m["name"],
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", ""),
                })
            return {"status": "online", "modelos": modelos}
    except Exception as e:
        return {"status": "offline", "modelos": [], "erro": str(e)}


@router.get("/finetuned/modelos")
async def listar_modelos_finetuned(db: AsyncSession = Depends(get_db)):
    """Lista modelos fine-tuned disponíveis (treinamentos concluídos)."""
    from sqlalchemy import select, desc
    from app.models.models import FineTuningJob

    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.status == "concluido")
        .order_by(desc(FineTuningJob.concluido_em))
    )
    jobs = result.scalars().all()

    modelos = []
    for job in jobs:
        if job.caminho_modelo and os.path.exists(job.caminho_modelo):
            adapter_config = os.path.join(job.caminho_modelo, "adapter_config.json")
            if os.path.exists(adapter_config):
                base_name = job.modelo_base.split("/")[-1] if "/" in job.modelo_base else job.modelo_base
                modelos.append({
                    "name": f"finetuned-{base_name}-job{job.id}",
                    "display_name": f"{base_name} (Fine-Tuned #{job.id})",
                    "job_id": job.id,
                    "modelo_base": job.modelo_base,
                    "caminho": job.caminho_modelo,
                    "loss_final": job.loss_atual,
                    "dataset_size": job.dataset_size,
                    "concluido_em": str(job.concluido_em) if job.concluido_em else None,
                })

    return {"status": "online" if modelos else "vazio", "modelos": modelos}


@router.get("/openai/modelos")
async def listar_modelos_openai(db: AsyncSession = Depends(get_db)):
    """Lista modelos disponíveis na API OpenAI."""
    config = await ConfigService.obter_ativa(db)
    settings = get_settings()
    api_key = (config.api_key if config else None) or settings.openai_api_key

    if not api_key or api_key == "sk-sua-chave-aqui":
        return {"status": "sem_api_key", "modelos": []}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 401:
                return {"status": "api_key_invalida", "modelos": []}

            data = resp.json()
            chat_prefixes = ("gpt-4", "gpt-3.5", "o1", "o3")
            modelos = []
            for m in data.get("data", []):
                mid = m["id"]
                if any(mid.startswith(p) for p in chat_prefixes):
                    modelos.append({"name": mid})

            modelos.sort(key=lambda x: x["name"])
            return {"status": "online", "modelos": modelos}
    except Exception as e:
        return {"status": "erro", "modelos": [], "erro": str(e)}
