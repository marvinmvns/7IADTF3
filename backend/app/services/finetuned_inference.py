"""Serviço de inferência com modelo fine-tuned (LoRA + base model)."""
import logging
import os
from pathlib import Path
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import FineTuningJob

logger = logging.getLogger("medassist.finetuned")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "models" / "finetuned"

# Cache global do modelo carregado
_loaded_model = None
_loaded_tokenizer = None
_loaded_job_id = None


def _get_latest_model_path(db_result) -> tuple[str, int] | None:
    """Retorna o caminho do modelo fine-tuned mais recente concluído."""
    for job in db_result:
        if job.caminho_modelo and os.path.exists(job.caminho_modelo):
            adapter_config = os.path.join(job.caminho_modelo, "adapter_config.json")
            if os.path.exists(adapter_config):
                return job.caminho_modelo, job.id
    return None


async def get_finetuned_model_info(db: AsyncSession) -> dict | None:
    """Retorna info do modelo fine-tuned mais recente, se disponível."""
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.status == "concluido")
        .order_by(desc(FineTuningJob.concluido_em))
    )
    jobs = result.scalars().all()

    info = _get_latest_model_path(jobs)
    if not info:
        return None

    path, job_id = info
    job = next(j for j in jobs if j.id == job_id)
    return {
        "job_id": job.id,
        "modelo_base": job.modelo_base,
        "caminho": path,
        "loss_final": job.loss_atual,
        "dataset_size": job.dataset_size,
        "concluido_em": str(job.concluido_em),
    }


def _load_model(model_path: str, job_id: int):
    """Carrega modelo fine-tuned com PEFT (lazy loading, cached)."""
    global _loaded_model, _loaded_tokenizer, _loaded_job_id

    if _loaded_model is not None and _loaded_job_id == job_id:
        return _loaded_model, _loaded_tokenizer

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel
        import json

        # Ler adapter_config para saber o modelo base
        with open(os.path.join(model_path, "adapter_config.json")) as f:
            adapter_config = json.load(f)
        base_model_name = adapter_config.get("base_model_name_or_path", "")

        logger.info(f"Carregando modelo base: {base_model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name, trust_remote_code=True
        )

        logger.info(f"Carregando LoRA adapter de: {model_path}")
        model = PeftModel.from_pretrained(base_model, model_path)
        model.eval()

        _loaded_model = model
        _loaded_tokenizer = tokenizer
        _loaded_job_id = job_id

        logger.info(f"Modelo fine-tuned carregado (job #{job_id})")
        return model, tokenizer

    except Exception as e:
        logger.error(f"Falha ao carregar modelo fine-tuned: {e}")
        return None, None


async def gerar_resposta_finetuned(
    db: AsyncSession, pergunta: str, contexto: str = "", max_tokens: int = 512
) -> str | None:
    """Gera resposta usando o modelo fine-tuned. Retorna None se indisponível."""
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.status == "concluido")
        .order_by(desc(FineTuningJob.concluido_em))
    )
    jobs = result.scalars().all()

    info = _get_latest_model_path(jobs)
    if not info:
        return None

    path, job_id = info

    try:
        import torch

        model, tokenizer = _load_model(path, job_id)
        if model is None:
            return None

        # Formata prompt no mesmo formato usado no treinamento
        prompt = f"### Instrução: {pergunta}\n"
        if contexto:
            prompt += f"### Contexto: {contexto}\n"
        prompt += "### Resposta:"

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,
            )

        # Decodifica apenas os tokens gerados (exclui o prompt)
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        resposta = tokenizer.decode(generated, skip_special_tokens=True).strip()

        logger.info(f"Fine-tuned respondeu ({len(resposta)} chars) para: '{pergunta[:50]}...'")
        return resposta

    except Exception as e:
        logger.error(f"Inferência fine-tuned falhou: {e}")
        return None


async def _load_finetuned_as_llm(db: AsyncSession, model_name: str = None,
                                  temperature: float = 0.7, max_tokens: int = 2048):
    """Carrega modelo fine-tuned como LLM compatível com LangChain.

    Retorna um ChatOpenAI apontando para o modelo fine-tuned servido localmente,
    ou um wrapper HuggingFace se o modelo estiver disponível apenas como adapter PEFT.
    """
    from langchain_community.llms import HuggingFacePipeline
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage
    from langchain_core.outputs import ChatResult, ChatGeneration

    # Busca job específico ou o mais recente
    job_id = None
    if model_name and "job" in model_name:
        import re
        match = re.search(r"job(\d+)", model_name)
        if match:
            job_id = int(match.group(1))

    if job_id:
        result = await db.execute(
            select(FineTuningJob).where(FineTuningJob.id == job_id, FineTuningJob.status == "concluido")
        )
        job = result.scalar_one_or_none()
        if not job or not job.caminho_modelo or not os.path.exists(job.caminho_modelo):
            raise ValueError(f"Modelo fine-tuned job#{job_id} não encontrado")
        model_path = job.caminho_modelo
        actual_job_id = job_id
    else:
        result = await db.execute(
            select(FineTuningJob)
            .where(FineTuningJob.status == "concluido")
            .order_by(desc(FineTuningJob.concluido_em))
        )
        jobs = result.scalars().all()
        info = _get_latest_model_path(jobs)
        if not info:
            raise ValueError("Nenhum modelo fine-tuned disponível")
        model_path, actual_job_id = info

    model, tokenizer = _load_model(model_path, actual_job_id)
    if model is None:
        raise ValueError(f"Falha ao carregar modelo fine-tuned de {model_path}")

    # Wrapper LangChain para o modelo PEFT
    class FineTunedChatModel(BaseChatModel):
        """Chat model wrapper para modelo fine-tuned com PEFT/LoRA."""

        @property
        def _llm_type(self) -> str:
            return "finetuned-peft"

        def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
            import torch

            # Extrai o conteúdo da última mensagem
            pergunta = messages[-1].content if messages else ""
            prompt = f"### Instrução: {pergunta}\n### Resposta:"

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=tokenizer.eos_token_id,
                )

            generated = outputs[0][inputs["input_ids"].shape[1]:]
            resposta = tokenizer.decode(generated, skip_special_tokens=True).strip()

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=resposta))])

    logger.info(f"Modelo fine-tuned carregado como LLM principal (job #{actual_job_id})")
    return FineTunedChatModel()
