"""Serviço de Fine-Tuning com PEFT/LoRA para modelos pequenos e modernos."""
import asyncio
import json
import math
import os
import re
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Event, Lock, Thread

# Fuso horário de Brasília (GMT-3) — naive para colunas TIMESTAMP WITHOUT TIME ZONE
BRT = timezone(timedelta(hours=-3))


def _now_brt():
    return datetime.now(BRT).replace(tzinfo=None)

# Configura ambiente para Intel XPU (Arc A770) via PyTorch nativo
# LD_PRELOAD do libstdc++ do sistema resolve conflito com anaconda
os.environ.setdefault("ZE_ENABLE_SYSMAN", "1")
os.environ.setdefault("ONEAPI_DEVICE_SELECTOR", "level_zero:0")

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.models import FineTuningJob, DatasetEntry

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "models" / "finetuned"
DATA_DIR = BASE_DIR / "app" / "data"

# Modelos recomendados: pequenos, modernos, eficientes em CPU/XPU
MODELOS_DISPONIVEIS = [
    {
        "id": "Qwen/Qwen3.5-9B",
        "nome": "Qwen 3.5 9B",
        "parametros": "9B",
        "ollama_model": "",
        "gguf_file": "Qwen3.5-9B-Q4_K_M.gguf",
        "descricao": "Modelo mais capaz da família Qwen 3.5. Melhor qualidade para fine-tuning médico avançado.",
        "ram_estimada": "~6 GB",
        "vram_treino": "~36 GB",
        "dispositivo": "CPU (não cabe na A770 para treino)",
    },
    {
        "id": "Qwen/Qwen3.5-4B",
        "nome": "Qwen 3.5 4B",
        "parametros": "4B",
        "ollama_model": "qwen3.5:4b",
        "gguf_file": "Qwen3.5-4B-Q4_K_M.gguf",
        "descricao": "Bom equilíbrio qualidade/velocidade. Fine-tuning médico rápido.",
        "ram_estimada": "~4 GB",
        "vram_treino": "~16 GB",
        "dispositivo": "CPU ou GPU (apertado na A770 16GB)",
    },
    {
        "id": "Qwen/Qwen2.5-3B-Instruct",
        "nome": "Qwen 2.5 3B Instruct",
        "parametros": "3B",
        "ollama_model": "qwen2.5:3b",
        "gguf_file": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        "descricao": "Compacto e eficiente. Cabe na A770 para treino LoRA. Ideal para fine-tuning médico.",
        "ram_estimada": "~3 GB",
        "vram_treino": "~12 GB",
        "dispositivo": "GPU (Intel Arc A770)",
    },
    {
        "id": "LiquidAI/LFM2.5-1.2B-Thinking",
        "nome": "LFM 2.5 1.2B Thinking",
        "parametros": "1.2B",
        "ollama_model": "",
        "gguf_file": "LFM2.5-1.2B-Thinking-Q4_K_M.gguf",
        "descricao": "Liquid AI — ultra-leve com reasoning. Treino rápido na GPU.",
        "ram_estimada": "~1.5 GB",
        "vram_treino": "~5 GB",
        "dispositivo": "GPU (Intel Arc A770)",
    },
]

# Registro de jobs em execução (para cancelamento)
_jobs_ativos: dict[int, bool] = {}


def anonimizar_texto(texto: str) -> str:
    """Anonimiza dados sensíveis no texto."""
    texto = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", "[CPF_ANONIMIZADO]", texto)
    texto = re.sub(r"(?:Dr\.|Dra\.|Sr\.|Sra\.)\s+[A-Z][a-záéíóú]+", "[NOME_ANONIMIZADO]", texto)
    return texto


async def carregar_dataset(db: AsyncSession) -> list[dict]:
    """Carrega dataset do banco de dados. Se vazio, importa do JSON."""
    result = await db.execute(
        select(DatasetEntry).where(DatasetEntry.ativo == True)
    )
    entries = result.scalars().all()

    if not entries:
        entries = await importar_dataset_json(db)

    dados = []
    for e in entries:
        dados.append({
            "instruction": anonimizar_texto(e.pergunta),
            "input": anonimizar_texto(e.contexto or ""),
            "output": anonimizar_texto(e.resposta),
        })
    return dados


async def importar_dataset_json(db: AsyncSession) -> list[DatasetEntry]:
    """Importa o dataset sintético JSON para o banco."""
    path = DATA_DIR / "dataset_sintetico.json"
    if not path.exists():
        return []

    with open(path) as f:
        dados = json.load(f)

    entries = []
    for item in dados:
        entry = DatasetEntry(
            pergunta=item.get("pergunta", ""),
            contexto=item.get("contexto", ""),
            resposta=item.get("resposta", ""),
            categoria="protocolo_medico",
        )
        db.add(entry)
        entries.append(entry)

    await db.commit()
    for e in entries:
        await db.refresh(e)
    return entries


def _atualizar_job_sync(job_id: int, **kwargs):
    """Atualiza job de forma síncrona (para uso em thread de treinamento)."""
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    with SyncSession(engine) as session:
        session.execute(
            update(FineTuningJob).where(FineTuningJob.id == job_id).values(**kwargs)
        )
        session.commit()
    engine.dispose()


def _gerenciar_llama_server(acao: str) -> tuple[bool, str]:
    """Para ou inicia o llama-server via Docker CLI (síncrono, para uso em thread)."""
    import subprocess
    try:
        # Encontra o container
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=llama-server", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        container = None
        for line in result.stdout.strip().split("\n"):
            if "llama-server" in line and "qwen" not in line and "lfm" not in line:
                container = line.strip()
                break

        if not container:
            return False, "Container llama-server não encontrado"

        result = subprocess.run(
            ["docker", acao, container],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return True, f"llama-server {acao} OK"
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _executar_treinamento(job_id: int, modelo_base: str, dados: list[dict], config: dict):
    """Executa o treinamento em thread separada."""
    log_lock = Lock()

    def append_log(msg: str):
        """Acumula log e atualiza no banco."""
        nonlocal logs
        with log_lock:
            logs += msg.rstrip("\n") + "\n"
            _atualizar_job_sync(job_id, logs=logs)

    def append_timed_log(msg: str):
        append_log(f"[{_now_brt().strftime('%H:%M:%S')}] {msg}")

    logs = ""
    llama_server_was_running = False
    try:
        _atualizar_job_sync(
            job_id,
            status="treinando",
            iniciado_em=_now_brt(),
            dataset_size=len(dados),
        )
        append_log(f"[{_now_brt().strftime('%H:%M:%S')}] Iniciando fine-tuning...")
        append_log(f"Modelo base: {modelo_base}")
        append_log(f"Dataset: {len(dados)} exemplos")
        append_log(f"Configuração: épocas={config['epocas']}, lr={config['learning_rate']}, "
                    f"LoRA r={config['lora_r']}, alpha={config['lora_alpha']}")

        # Desliga o llama-server para liberar VRAM da GPU
        append_timed_log("Desligando llama-server para liberar VRAM da GPU...")
        ok, msg = _gerenciar_llama_server("stop")
        if ok:
            llama_server_was_running = True
            append_timed_log("llama-server desligado. GPU totalmente livre para treino.")
            # Aguarda a GPU liberar memória
            time.sleep(3)
        else:
            append_log(f"[AVISO] llama-server: {msg} (continuando sem desligar)")

        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
            from peft import LoraConfig, get_peft_model, TaskType
            from datasets import Dataset
        except ImportError:
            append_log("[AVISO] Dependências de ML não instaladas. Executando simulação...")
            _simular_treinamento(job_id, modelo_base, dados, config, append_log)
            return

        # === Patches Intel XPU ===
        # torch.triu e torch.ones com bool não funcionam no XPU
        _original_triu = torch.triu
        def _patched_triu(input, diagonal=0, *, out=None):
            if input.device.type == "xpu" and input.dtype == torch.bool:
                return _original_triu(input.to("cpu"), diagonal=diagonal).to(input.device)
            return _original_triu(input, diagonal=diagonal, out=out)
        torch.triu = _patched_triu

        _original_ones = torch.ones
        def _patched_ones(*size, dtype=None, device=None, **kwargs):
            if device is not None and str(device).startswith("xpu") and dtype == torch.bool:
                return _original_ones(*size, dtype=dtype, device="cpu", **kwargs).to(device)
            return _original_ones(*size, dtype=dtype, device=device, **kwargs)
        torch.ones = _patched_ones

        # Patch Qwen3.5 Gated Delta Net: .contiguous().to(float32) falha no XPU.
        # Solução: executa chunk_gated_delta_rule na CPU e devolve resultado ao XPU.
        try:
            import transformers.models.qwen3_5.modeling_qwen3_5 as _qwen35_mod
            _orig_chunk_gated = _qwen35_mod.torch_chunk_gated_delta_rule

            def _patched_chunk_gated(*args, **kwargs):
                device = args[0].device if args else None
                cpu_args = [a.to("cpu") if isinstance(a, torch.Tensor) else a for a in args]
                cpu_kwargs = {k: v.to("cpu") if isinstance(v, torch.Tensor) else v for k, v in kwargs.items()}
                result = _orig_chunk_gated(*cpu_args, **cpu_kwargs)
                if device and device.type == "xpu":
                    if isinstance(result, tuple):
                        return tuple(r.to(device) if isinstance(r, torch.Tensor) else r for r in result)
                    return result.to(device) if isinstance(result, torch.Tensor) else result
                return result

            _qwen35_mod.torch_chunk_gated_delta_rule = _patched_chunk_gated
            # Também patcha a referência dentro da classe que usa
            if hasattr(_qwen35_mod, 'Qwen3_5LinearAttention'):
                _qwen35_mod.Qwen3_5LinearAttention.chunk_gated_delta_rule = staticmethod(_patched_chunk_gated)
            append_log("[PATCH] Qwen3.5 Gated Delta Net patcheado para Intel XPU")
        except (ImportError, AttributeError):
            pass  # Modelo não é Qwen3.5, patch não necessário

        # Carrega modelo
        append_log(f"\n[{_now_brt().strftime('%H:%M:%S')}] Baixando modelo {modelo_base}...")
        _atualizar_job_sync(job_id, progresso=5)

        tokenizer = AutoTokenizer.from_pretrained(modelo_base, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            modelo_base, trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
        )
        append_log(f"[{_now_brt().strftime('%H:%M:%S')}] Modelo carregado.")
        _atualizar_job_sync(job_id, progresso=15)

        # Configura LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=config["lora_r"],
            lora_alpha=config["lora_alpha"],
            lora_dropout=0.1,
            target_modules="all-linear",
        )
        model = get_peft_model(model, lora_config)

        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        append_log(f"Parâmetros treináveis: {trainable_params:,} / {total_params:,} "
                    f"({100 * trainable_params / total_params:.2f}%)")
        _atualizar_job_sync(job_id, progresso=20)

        # Prepara dataset
        def tokenizar(exemplo):
            texto = f"### Instrução: {exemplo['instruction']}\n"
            if exemplo["input"]:
                texto += f"### Contexto: {exemplo['input']}\n"
            texto += f"### Resposta: {exemplo['output']}"
            tokens = tokenizer(
                texto, truncation=True, max_length=config["max_length"], padding="max_length"
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        dataset = Dataset.from_list(dados)
        dataset = dataset.map(tokenizar, remove_columns=dataset.column_names)
        append_log(f"[{_now_brt().strftime('%H:%M:%S')}] Dataset tokenizado.")
        _atualizar_job_sync(job_id, progresso=25)

        # Treinamento
        output_dir = str(OUTPUT_DIR / f"job-{job_id}")
        os.makedirs(output_dir, exist_ok=True)

        epocas = config["epocas"]
        steps_por_epoca = max(1, math.ceil(len(dataset) / max(config["batch_size"], 1)))
        steps_totais_estimados = steps_por_epoca * epocas
        append_log(
            f"Estimativa de treino: ~{steps_por_epoca} steps/época, "
            f"~{steps_totais_estimados} steps no total."
        )

        # Estima tamanho do modelo para decidir dispositivo
        total_params = sum(p.numel() for p in model.parameters())
        modelo_bilhoes = total_params / 1e9

        # Detecta dispositivo: Intel XPU > CUDA > CPU
        # O llama-server já foi desligado, então a GPU está totalmente livre
        device_type = "cpu"
        try:
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                gpu_name = torch.xpu.get_device_name(0)
                gpu_mem_total = torch.xpu.get_device_properties(0).total_memory / 1024**3
                # bf16: ~2 bytes/param + gradientes + LoRA adapters + optimizer states
                vram_necessaria = modelo_bilhoes * 4.0

                if vram_necessaria > gpu_mem_total:
                    append_log(
                        f"Dispositivo: Intel XPU - {gpu_name} ({gpu_mem_total:.1f} GB). "
                        f"Modelo {modelo_bilhoes:.1f}B precisa de ~{vram_necessaria:.0f} GB. Usando CPU."
                    )
                    device_type = "cpu"
                else:
                    device_type = "xpu"
                    append_log(
                        f"Dispositivo: Intel XPU - {gpu_name} ({gpu_mem_total:.1f} GB livre, "
                        f"modelo {modelo_bilhoes:.1f}B precisa de ~{vram_necessaria:.0f} GB)"
                    )
                    model = model.to("xpu")
            elif torch.cuda.is_available():
                device_type = "cuda"
                append_log(f"Dispositivo: CUDA - {torch.cuda.get_device_name(0)}")
            else:
                append_log("Dispositivo: CPU")
        except Exception as e:
            append_log(f"Dispositivo: CPU (erro na detecção: {e})")

        # Gradient checkpointing para reduzir uso de memória
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()
            append_log("Gradient checkpointing ativado (economia de memória)")

        treino_estado = {
            "device": device_type,
            "first_step_started": False,
            "started_at_monotonic": None,
        }

        from transformers import TrainerCallback

        class ProgressTrainerCallback(TrainerCallback):
            def on_train_begin(self, args, state, control, **kwargs):
                append_timed_log(
                    f"Trainer pronto em {treino_estado['device'].upper()}. "
                    f"Estimativa: {steps_totais_estimados} steps totais."
                )

            def on_epoch_begin(self, args, state, control, **kwargs):
                epoca_idx = min(epocas, max(1, int(state.epoch or 0) + 1))
                append_timed_log(f"Época {epoca_idx}/{epocas} iniciada.")

            def on_step_begin(self, args, state, control, **kwargs):
                if not treino_estado["first_step_started"]:
                    treino_estado["first_step_started"] = True
                    append_timed_log(
                        f"Primeiro step iniciado em {treino_estado['device'].upper()}."
                    )

            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and "loss" in logs:
                    loss = logs["loss"]
                    step = state.global_step
                    total = state.max_steps
                    epoch = state.epoch or 0
                    epoca_atual = 0 if step == 0 else min(epocas, max(1, math.ceil(epoch)))
                    pct = int(25 + (step / max(total, 1)) * 70)
                    _atualizar_job_sync(
                        job_id,
                        progresso=min(pct, 95),
                        epoca_atual=epoca_atual,
                        loss_atual=round(loss, 4),
                    )
                    append_log(f"  Step {step}/{total} | Época {epoch:.1f} | Loss: {loss:.4f}")

            def on_train_end(self, args, state, control, **kwargs):
                append_timed_log("Treinamento finalizado. Salvando adaptadores LoRA...")

        def _criar_trainer(use_device):
            """Cria trainer para o dispositivo especificado."""
            nonlocal model
            tkwargs = {
                "output_dir": output_dir,
                "num_train_epochs": epocas,
                "per_device_train_batch_size": config["batch_size"],
                "learning_rate": config["learning_rate"],
                "logging_steps": 1,
                "logging_first_step": True,
                "save_strategy": "epoch",
                "report_to": "none",
                "dataloader_pin_memory": False,
                "optim": "adamw_torch",
            }
            if use_device == "cpu":
                tkwargs["use_cpu"] = True
                tkwargs["fp16"] = False
                tkwargs["bf16"] = False
            else:
                tkwargs["bf16"] = True
                tkwargs["fp16"] = False
            return Trainer(
                model=model,
                args=TrainingArguments(**tkwargs),
                train_dataset=dataset,
                callbacks=[ProgressTrainerCallback()],
            )

        def _treinar_com_heartbeat(trainer, use_device):
            treino_estado["device"] = use_device
            treino_estado["first_step_started"] = False
            treino_estado["started_at_monotonic"] = time.monotonic()
            heartbeat_stop = Event()

            def _heartbeat():
                while not heartbeat_stop.wait(20):
                    if treino_estado["first_step_started"]:
                        continue
                    elapsed = int(time.monotonic() - treino_estado["started_at_monotonic"])
                    minutos, segundos = divmod(elapsed, 60)
                    if use_device == "cpu":
                        append_timed_log(
                            "Treino em CPU ainda preparando o primeiro step "
                            f"({minutos}m{segundos:02d}s decorridos). "
                            "Para um modelo 4B isso pode levar vários minutos."
                        )
                    else:
                        append_timed_log(
                            f"Treino em {use_device.upper()} ainda preparando o primeiro step "
                            f"({minutos}m{segundos:02d}s decorridos)."
                        )

            heartbeat_thread = Thread(target=_heartbeat, daemon=True)
            heartbeat_thread.start()
            try:
                trainer.train()
            finally:
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)

        append_log(f"\n[{_now_brt().strftime('%H:%M:%S')}] Iniciando treinamento...")

        # Tenta XPU/CUDA primeiro; se falhar (UR error / OOM), faz fallback para CPU
        try:
            trainer = _criar_trainer(device_type)
            _treinar_com_heartbeat(trainer, device_type)
        except RuntimeError as e:
            err_str = str(e)
            if device_type != "cpu" and ("UR error" in err_str or "XPU" in err_str or "OUT_OF" in err_str):
                append_log(f"\n[AVISO] {device_type.upper()} falhou ({e.__class__.__name__}). Fazendo fallback para CPU...")
                _atualizar_job_sync(job_id, progresso=25)

                # Tenta mover para CPU; se falhar (memória corrompida), recria do zero
                try:
                    try:
                        del trainer
                    except (UnboundLocalError, NameError):
                        pass
                    model = model.to("cpu")
                    if hasattr(torch, "xpu"):
                        torch.xpu.empty_cache()
                    append_timed_log("Pesos movidos para CPU com sucesso.")
                except Exception as move_err:
                    append_log(f"[AVISO] Não foi possível mover modelo ({move_err}). Recriando do zero em CPU...")
                    # Libera tudo e recria
                    try:
                        del model
                    except (UnboundLocalError, NameError):
                        pass
                    try:
                        del trainer
                    except (UnboundLocalError, NameError):
                        pass
                    if hasattr(torch, "xpu"):
                        torch.xpu.empty_cache()
                    import gc
                    gc.collect()

                    # Recarrega modelo na CPU
                    append_timed_log("Recarregando modelo base na CPU...")
                    model = AutoModelForCausalLM.from_pretrained(
                        modelo_base, trust_remote_code=True,
                        torch_dtype=torch.float32,
                        attn_implementation="eager",
                    )
                    model = get_peft_model(model, lora_config)
                    if hasattr(model, "gradient_checkpointing_enable"):
                        model.gradient_checkpointing_enable()
                    append_timed_log("Modelo recriado na CPU.")

                device_type = "cpu"
                append_timed_log(
                    "Trainer recriado em CPU. O primeiro step pode demorar vários minutos; "
                    "o log continuará sendo atualizado durante essa preparação."
                )
                trainer = _criar_trainer("cpu")
                _treinar_com_heartbeat(trainer, "cpu")
            else:
                raise

        # Salva modelo
        save_path = os.path.join(output_dir, "medassist-lora")
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        append_log(f"\n[{_now_brt().strftime('%H:%M:%S')}] Modelo salvo em: {save_path}")

        _atualizar_job_sync(
            job_id,
            status="concluido",
            progresso=100,
            caminho_modelo=save_path,
            concluido_em=_now_brt(),
        )
        append_log(f"[{_now_brt().strftime('%H:%M:%S')}] Fine-tuning concluído com sucesso!")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logs += f"\n[ERRO] {error_msg}\n{traceback.format_exc()}"
        _atualizar_job_sync(
            job_id,
            status="erro",
            erro_msg=error_msg,
            logs=logs,
            concluido_em=_now_brt(),
        )
    finally:
        _jobs_ativos.pop(job_id, None)
        # Religa o llama-server se estava rodando antes do treino
        if llama_server_was_running:
            try:
                logs += f"[{_now_brt().strftime('%H:%M:%S')}] Religando llama-server...\n"
                _atualizar_job_sync(job_id, logs=logs)
                ok, msg = _gerenciar_llama_server("start")
                if ok:
                    logs += f"[{_now_brt().strftime('%H:%M:%S')}] llama-server religado com sucesso.\n"
                else:
                    logs += f"[AVISO] Falha ao religar llama-server: {msg}\n"
                _atualizar_job_sync(job_id, logs=logs)
            except Exception:
                pass


def _simular_treinamento(job_id: int, modelo_base: str, dados: list[dict], config: dict, append_log):
    """Simulação do treinamento para ambientes sem dependências ML."""
    import time

    epocas = config["epocas"]
    total_steps = len(dados) * epocas // config["batch_size"]
    total_steps = max(total_steps, 1)

    append_log(f"\n[SIMULAÇÃO] Treinamento com {total_steps} steps")
    loss = 2.5

    for step in range(1, total_steps + 1):
        if job_id not in _jobs_ativos:
            append_log("[CANCELADO] Treinamento interrompido pelo usuário.")
            _atualizar_job_sync(job_id, status="erro", erro_msg="Cancelado pelo usuário")
            return

        time.sleep(0.5)
        loss *= 0.92
        epoch = step * epocas / total_steps
        pct = int(25 + (step / total_steps) * 70)

        _atualizar_job_sync(
            job_id,
            progresso=min(pct, 95),
            epoca_atual=int(epoch),
            loss_atual=round(loss, 4),
        )
        append_log(f"  [SIM] Step {step}/{total_steps} | Época {epoch:.1f} | Loss: {loss:.4f}")

    output_dir = str(OUTPUT_DIR / f"job-{job_id}")
    os.makedirs(output_dir, exist_ok=True)

    resultado = {
        "status": "simulado",
        "modelo_base": modelo_base,
        "tecnica": "LoRA (PEFT)",
        "epocas": epocas,
        "lr": config["learning_rate"],
        "lora_r": config["lora_r"],
        "lora_alpha": config["lora_alpha"],
        "dataset_size": len(dados),
        "loss_final": round(loss, 4),
    }
    with open(os.path.join(output_dir, "resultado_simulacao.json"), "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    _atualizar_job_sync(
        job_id,
        status="concluido",
        progresso=100,
        caminho_modelo=output_dir,
        concluido_em=_now_brt(),
    )
    append_log(f"\n[{_now_brt().strftime('%H:%M:%S')}] Simulação concluída com sucesso!")


async def gerar_dataset_por_doenca(db: AsyncSession, doenca: str) -> list[DatasetEntry]:
    """Gera entradas de dataset automaticamente buscando informações sobre uma doença no PubMed."""
    import httpx
    from bs4 import BeautifulSoup

    perguntas_template = [
        "Quais são os sintomas de {doenca}?",
        "Como é feito o diagnóstico de {doenca}?",
        "Qual o tratamento para {doenca}?",
        "Quais são as complicações de {doenca}?",
        "Qual a fisiopatologia de {doenca}?",
    ]

    # Search PubMed for article IDs
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={doenca}&retmax=5&retmode=json"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        search_resp = await client.get(search_url)
        search_data = search_resp.json()
        ids = search_data.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # Fetch article details
        ids_str = ",".join(ids)
        fetch_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={ids_str}&retmode=xml"
        )
        fetch_resp = await client.get(fetch_url)

    soup = BeautifulSoup(fetch_resp.text, "html.parser")
    articles = soup.find_all("pubmedarticle")

    entries = []
    for i, article in enumerate(articles):
        # Extract title
        title_tag = article.find("articletitle")
        titulo = title_tag.get_text(strip=True) if title_tag else f"Artigo sobre {doenca}"

        # Extract abstract
        abstract_tag = article.find("abstracttext")
        abstract = abstract_tag.get_text(strip=True) if abstract_tag else ""

        if not abstract:
            continue

        # Use a varied question for each article
        pergunta = perguntas_template[i % len(perguntas_template)].format(doenca=doenca)

        entry = DatasetEntry(
            pergunta=pergunta,
            contexto=f"PubMed - {titulo}",
            resposta=abstract,
            categoria="pesquisa_medica",
        )
        db.add(entry)
        entries.append(entry)

    await db.commit()
    for e in entries:
        await db.refresh(e)
    return entries


async def iniciar_finetuning(db: AsyncSession, config: dict) -> FineTuningJob:
    """Cria um job de fine-tuning e inicia em background."""
    dados = await carregar_dataset(db)
    if not dados:
        raise ValueError("Dataset vazio. Adicione exemplos antes de iniciar o fine-tuning.")

    job = FineTuningJob(
        modelo_base=config["modelo_base"],
        epocas_total=config["epocas"],
        learning_rate=config["learning_rate"],
        lora_r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        batch_size=config["batch_size"],
        max_length=config["max_length"],
        dataset_size=len(dados),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    _jobs_ativos[job.id] = True
    thread = Thread(
        target=_executar_treinamento,
        args=(job.id, config["modelo_base"], dados, config),
        daemon=True,
    )
    thread.start()

    return job


async def cancelar_job(job_id: int, db: AsyncSession) -> bool:
    """Cancela um job em execução."""
    if job_id in _jobs_ativos:
        del _jobs_ativos[job_id]
    await db.execute(
        update(FineTuningJob)
        .where(FineTuningJob.id == job_id)
        .values(status="erro", erro_msg="Cancelado pelo usuário", concluido_em=_now_brt())
    )
    await db.commit()
    return True
