"""Pipeline de Fine-Tuning de LLM com dados médicos.

Utiliza PEFT/LoRA para fine-tuning eficiente em CPU.
Datasets: PubMedQA, MedQuAD e dados sintéticos do hospital.
"""
import json
import os
from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
OUTPUT_DIR = BASE_DIR / "models" / "finetuned"


def carregar_dataset_sintetico() -> list[dict]:
    """Carrega dataset sintético de dados médicos do hospital."""
    path = DATA_DIR / "dataset_sintetico.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def preparar_dados_treinamento(dados: list[dict]) -> list[dict]:
    """Prepara dados no formato instruction/input/output para fine-tuning."""
    formatados = []
    for item in dados:
        formatados.append({
            "instruction": item.get("pergunta", ""),
            "input": item.get("contexto", ""),
            "output": item.get("resposta", ""),
        })
    return formatados


def anonimizar_dados(dados: list[dict]) -> list[dict]:
    """Anonimiza dados sensíveis (nomes, CPFs, etc)."""
    import re
    anonimizados = []
    for item in dados:
        texto = json.dumps(item, ensure_ascii=False)
        # Remove CPFs
        texto = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", "[CPF_ANONIMIZADO]", texto)
        # Remove nomes próprios (simplificado)
        texto = re.sub(r"(?:Dr\.|Dra\.|Sr\.|Sra\.)\s+[A-Z][a-záéíóú]+", "[NOME_ANONIMIZADO]", texto)
        anonimizados.append(json.loads(texto))
    return anonimizados


def executar_fine_tuning(model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
    """Executa fine-tuning com PEFT/LoRA (compatível com CPU)."""
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import Dataset
    except ImportError:
        print("Instale: pip install transformers peft datasets")
        print("Executando em modo simulação...")
        return _simular_fine_tuning()

    print(f"Carregando modelo base: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    # Configuração LoRA (eficiente para CPU)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Prepara dataset
    dados = carregar_dataset_sintetico()
    dados = anonimizar_dados(dados)
    dados_treino = preparar_dados_treinamento(dados)

    def tokenizar(exemplo):
        texto = f"### Instrução: {exemplo['instruction']}\n"
        if exemplo["input"]:
            texto += f"### Contexto: {exemplo['input']}\n"
        texto += f"### Resposta: {exemplo['output']}"
        return tokenizer(texto, truncation=True, max_length=512, padding="max_length")

    dataset = Dataset.from_list(dados_treino)
    dataset = dataset.map(tokenizar)

    # Treinamento
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=2,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        no_cuda=True,  # CPU only
    )

    trainer = Trainer(model=model, args=args, train_dataset=dataset)
    trainer.train()
    model.save_pretrained(OUTPUT_DIR / "medassist-lora")
    tokenizer.save_pretrained(OUTPUT_DIR / "medassist-lora")
    print(f"Modelo salvo em: {OUTPUT_DIR / 'medassist-lora'}")


def _simular_fine_tuning():
    """Simulação do fine-tuning para ambientes sem GPU/dependências."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    resultado = {
        "status": "simulado",
        "modelo_base": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "tecnica": "LoRA (PEFT)",
        "epocas": 3,
        "lr": 2e-4,
        "lora_r": 8,
        "dataset_size": len(carregar_dataset_sintetico()),
        "nota": "Execute com dependências instaladas para treinamento real",
    }
    with open(OUTPUT_DIR / "resultado_simulacao.json", "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("Simulação concluída:", json.dumps(resultado, indent=2, ensure_ascii=False))
    return resultado


if __name__ == "__main__":
    executar_fine_tuning()
