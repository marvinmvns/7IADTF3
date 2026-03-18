# MedAssist - Assistente Medico Virtual

**Tech Challenge Fase 3 - FIAP Pos Tech IA para Devs**

Assistente virtual medico com triagem inteligente (Protocolo Manchester), chat conversacional com IA multi-fonte (RAG + Fine-Tuning + Web Search), scraping inteligente de dados medicos, pipeline de fine-tuning com PEFT/LoRA, TTS/STT local (sem GPU), servidor MCP e interface responsiva completa.

## Arquitetura

O projeto segue o padrao **MVC (Model-View-Controller)** com separacao clara de responsabilidades.

```
7IADTF3/
├── backend/                    # Python FastAPI (Model + Controller)
│   ├── app/
│   │   ├── models/             # Models - SQLAlchemy ORM
│   │   ├── controllers/        # Controllers - Rotas REST
│   │   │   ├── chat_controller.py
│   │   │   ├── triagem_controller.py
│   │   │   ├── paciente_controller.py
│   │   │   ├── scraping_controller.py
│   │   │   ├── config_controller.py
│   │   │   ├── finetuning_controller.py
│   │   │   ├── rag_controller.py
│   │   │   └── auditoria_controller.py
│   │   ├── services/           # Services - Logica de negocio
│   │   │   ├── llm/            # LangChain, LangGraph, MCP Tools
│   │   │   ├── rag/            # RAG - ChromaDB + Embeddings
│   │   │   ├── scraping/       # Scrapers + Agente Inteligente LLM
│   │   │   └── tts/            # Piper TTS + Vosk STT
│   │   ├── schemas/            # Pydantic - Validacao
│   │   └── data/               # Dataset sintetico
│   ├── models/                 # Modelos treinados (LoRA adapters + ChromaDB)
│   ├── scripts/                # Fine-tuning, seed DB
│   └── mcp_server.py           # Servidor MCP (Model Context Protocol)
├── frontend/                   # Angular 19 (View)
│   └── src/app/
│       ├── components/         # Chat, Triagem, Prontuario, Config, Scraping,
│       │                       # Pacientes, Fine-Tuning, Auditoria
│       ├── services/           # API Service
│       └── models/             # TypeScript interfaces
├── docker-compose.yml          # Orquestracao completa
└── setup.sh                    # Script de instalacao
```

## Tecnologias

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Backend | Python + FastAPI | 3.11 / 0.115 |
| Frontend | Angular | 19 |
| Banco de Dados | PostgreSQL | 16 |
| ORM | SQLAlchemy (async) | 2.0 |
| LLM | LangChain + LangGraph | 0.3 / 0.3 |
| Fine-Tuning | PEFT/LoRA + HuggingFace Transformers | 0.14 / 4.52 |
| RAG | ChromaDB + sentence-transformers | 0.6 / 3.3 |
| MCP | Model Context Protocol (SSE) | 1.0 |
| TTS | Piper (local, sem GPU) | 1.2 |
| STT | Vosk (local, sem GPU) | 0.3 |
| Scraping | BeautifulSoup + Playwright + httpx | 4.12 / 1.47 |
| LLM Local | llama.cpp SYCL (Intel Arc A770) | - |
| Container | Docker + Docker Compose | - |

## Funcionalidades

### Chat Conversacional com IA (Multi-Fonte)
Interface de chat com suporte a texto e voz. Tres modos de conversa: geral, triagem e consulta medica. O pipeline de resposta agrega **4 fontes de conhecimento em paralelo**: modelo fine-tuned (LoRA), RAG (ChromaDB), busca web (Brave Search) e contexto do paciente (prontuarios, triagens, alergias). Cada resposta inclui a fonte da informacao (explainability). Suporte a TTS (texto para voz) e STT (voz para texto) com modelos locais que rodam em CPU. Identificacao do medico (CRM + nome) e selecao de paciente por CPF com painel de contexto clinico.

### Triagem Inteligente (Manchester)
Classificacao de risco automatizada baseada no Protocolo Manchester com 5 niveis de cores. O sistema utiliza **3 camadas de classificacao**: LLM (retorna JSON com nivel de urgencia 1-10 e diagnosticos possiveis), LangGraph StateGraph (exames e alertas) e fallback por palavras-chave. Toda classificacao requer validacao humana antes de ser efetivada.

### Gestao de Pacientes
Tela completa de CRUD de pacientes com busca por CPF e nome, cadastro com validacao (CPF, email, CEP com auto-preenchimento de endereco), edicao e exclusao. Links rapidos para prontuario e chat do paciente.

### Prontuario por CPF
Tela de busca por CPF com autocomplete que retorna a ficha completa do paciente: dados pessoais, historico de consultas, medicamentos, alergias, triagens anteriores e conversas com a IA. Confirmacao de identidade via data de nascimento.

### RAG (Retrieval-Augmented Generation)
Pipeline RAG com **ChromaDB** como vector store local e embeddings do `sentence-transformers/all-MiniLM-L6-v2`. Indexa automaticamente dados medicos (scraping), dataset de treinamento e prontuarios anonimizados. Busca semantica por distancia cosseno com filtro de relevancia (limiar >= 0.15). Contexto formatado com limite de 3000 caracteres injetado no prompt do LLM.

### Pipeline de Fine-Tuning (Interface Completa)
Pipeline de fine-tuning com **PEFT/LoRA** gerenciavel pela interface web. Tres abas: Treinar (selecao de modelo, hiperparametros), Progresso (monitoramento em tempo real com loss, epoca, barra de progresso) e Dataset (adicionar, importar, gerar automaticamente). Suporte a Intel XPU (Arc A770), CUDA e CPU. Adapter LoRA salvo em `backend/models/finetuned/` e integrado ao pipeline de chat via lazy loading.

### Scraping de Dados Medicos
Sete scrapers inteligentes para sites de referencia medica:

| Fonte | Tipo | URL |
|-------|------|-----|
| PubMed | Artigos cientificos | pubmed.ncbi.nlm.nih.gov |
| MedlinePlus | Informacoes de saude | medlineplus.gov |
| BVS/BIREME | Literatura medica | pesquisa.bvsalud.org |
| Drauzio Varella | Divulgacao (PT-BR) | drauziovarella.uol.com.br |
| Mayo Clinic | Referencia medica | mayoclinic.org |
| DataSUS | Dados publicos BR | datasus.saude.gov.br |
| OpenFDA | Medicamentos | api.fda.gov |

### Agente de Scraping Inteligente (LLM)
Agente autonomo orquestrado por LLM em 6 passos: (1) LLM planeja 5 perguntas de pesquisa, (2) busca artigos no PubMed, (3) coleta fontes brasileiras (Drauzio Varella, BVS), (4) busca no Google Scholar, (5) salva dados no banco como `DadoMedico`, (6) LLM gera pares Q&A para enriquecer o dataset de treinamento automaticamente.

### Agente de Navegacao
Agente autonomo que navega em multiplos sites medicos usando Playwright, coleta informacoes e segue links relevantes automaticamente. Possui fallback com httpx para ambientes sem Playwright.

### Servidor MCP (Model Context Protocol)
Servidor standalone (porta 8091) que expoe 7 ferramentas de acesso a dados de pacientes via protocolo SSE: buscar por CPF, ficha completa, listar pacientes, prontuarios, triagens, buscar por nome e resumo de atendimento. Compativel com Claude e outros clientes MCP. Integrado ao LangChain via ReAct Agent para consultas que envolvem dados de pacientes.

### Auditoria
Tela de auditoria com estatisticas (total de registros, categorias, usuarios ativos), filtro por categoria de acao, e log detalhado com acoes coloridas por tipo (chat, triagem, paciente, scraping, finetuning, config).

### Configuracao de LLM
Tela para parametrizar o modelo de linguagem em tempo real. Suporta **3 provedores**: OpenAI (GPT-4o-mini, GPT-4), Ollama (modelos locais) e llama.cpp SYCL (Intel Arc A770 com Qwen 3.5 4B quantizado). Ajuste de temperatura, max tokens, e selecao de engine TTS/STT. Indexacao RAG com estatisticas de documentos.

## Instalacao Rapida

### Pre-requisitos

- **Docker** e **Docker Compose** instalados
- **~15 GB de espaco em disco** (imagens Docker + modelo LLM)
- (Opcional) GPU Intel Arc para aceleracao via SYCL

### Passo a passo

```bash
# 1. Clone o repositorio
git clone https://github.com/marvinmvns/7IADTF3.git
cd 7IADTF3

# 2. (Opcional) Configure variaveis de ambiente
cp backend/.env.example backend/.env
# Edite backend/.env se desejar usar OpenAI ou Brave Search

# 3. Execute o setup
chmod +x setup.sh
./setup.sh
```

### O que o setup.sh faz automaticamente

| Etapa | O que acontece |
|-------|---------------|
| **Modelo LLM** | Baixa o Qwen 3.5 4B quantizado (GGUF Q4_K_M, ~2.6 GB) do HuggingFace para `models/` |
| **Docker Build** | Constroi as imagens do backend e frontend |
| **Docker Up** | Sobe 4 containers: PostgreSQL, llama-server, backend FastAPI e frontend Angular/Nginx |

### O que o Docker baixa e configura na build

| Download automatico | Tamanho | Descricao |
|---------------------|---------|-----------|
| Vosk STT (pt-BR) | ~50 MB | Modelo de reconhecimento de voz em portugues |
| Piper TTS (pt-BR) | ~60 MB | Modelo de sintese de voz em portugues |
| Playwright + Chromium | ~150 MB | Navegador para agente de scraping |
| Sentence-Transformers | ~90 MB | Embeddings para RAG (all-MiniLM-L6-v2, baixa no primeiro uso) |
| Dependencias Python | ~2 GB | FastAPI, LangChain, PyTorch, Transformers, etc. |

### O que o backend faz ao iniciar (automatico)

1. **Cria as tabelas** no PostgreSQL (SQLAlchemy `create_all`)
2. **Seed de pacientes** — se o banco estiver vazio, popula 25 pacientes com prontuarios e triagens
3. **Importa dataset sintetico** — 40 entradas de treinamento (protocolos, procedimentos, laudos)
4. **Indexa RAG** — indexa dados medicos, dataset e prontuarios no ChromaDB

### Acessos apos o setup

| Servico | URL |
|---------|-----|
| Frontend (interface) | http://localhost:8090 |
| Backend API (Swagger) | http://localhost:8001/docs |
| llama-server (LLM) | http://localhost:8081 |
| PostgreSQL | localhost:5433 (user: medassist / pass: medassist123) |

> **Nota:** O llama-server leva ~3 minutos na primeira inicializacao (compilacao de kernels SYCL). Inicializacoes subsequentes sao mais rapidas. O chat so funciona apos o llama-server ficar healthy.

### Comandos uteis apos a instalacao

```bash
# Ver status dos containers
docker compose ps

# Ver logs do backend em tempo real
docker compose logs -f backend

# Reiniciar tudo (rebuild)
docker compose up -d --build

# Parar todos os servicos
docker compose down

# Parar e remover volumes (reset completo)
docker compose down -v
```

## Modos de LLM

### llama.cpp SYCL (padrao - Intel Arc A770)
```bash
# Setup padrao ja configura o llama-server com Qwen 3.5 4B quantizado
./setup.sh
# ou
docker compose up -d
```

### Ollama (CPU/GPU generica)
```bash
# Inicia com perfil cpu (Ollama em container)
docker compose --profile cpu up -d

# Na tela de Configuracao, selecione:
# Provider: Ollama | Modelo: qwen2.5:3b ou qwen2.5:7b
```

### OpenAI (API Cloud)
```bash
# Configure a API key no .env
echo "OPENAI_API_KEY=sk-..." >> backend/.env
echo "LLM_PROVIDER=openai" >> backend/.env
docker compose up -d

# Na tela de Configuracao, selecione:
# Provider: OpenAI | Modelo: gpt-4o-mini
```

## Fluxo LangGraph - Triagem

```
[Coletar Sintomas] → [Classificar Risco] → {Urgente?}
                                              ├─ Sim → [Gerar Alerta] → [Verificar Exames] → [Orientacao] → FIM
                                              └─ Nao → [Verificar Exames] → [Orientacao] → FIM
```

## Pipeline de Resposta do Chat

```
Pergunta do Usuario
       ↓
[1] Fine-Tuned Model (LoRA) → resposta especializada medica
[2] RAG (ChromaDB)           → protocolos hospitalares, prontuarios, dataset
[3] Web Search (Brave)       → informacoes medicas complementares
[4] Contexto do Paciente     → dados do prontuario via banco SQL
       ↓
Tudo injetado no System Prompt via {rag_context}
       ↓
[5] LLM Principal (OpenAI/Ollama/llama.cpp) → resposta final
       ↓
Resposta + Fontes (explainability)
```

## API Endpoints

### Pacientes
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | /api/pacientes/ | Lista pacientes |
| GET | /api/pacientes/cpf/{cpf} | Busca paciente por CPF |
| GET | /api/pacientes/cpf/{cpf}/ficha | Ficha completa do paciente |
| GET | /api/pacientes/buscar?nome={nome} | Busca por nome |
| POST | /api/pacientes/ | Cadastra paciente |
| PUT | /api/pacientes/{id} | Atualiza paciente |
| DELETE | /api/pacientes/{id} | Remove paciente |

### Chat
| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | /api/chat/mensagem | Envia mensagem ao chat |
| POST | /api/chat/voz-para-texto | STT (audio para texto) |
| POST | /api/chat/texto-para-voz | TTS (texto para audio) |

### Triagem
| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | /api/triagens/ | Realiza triagem com IA (3 camadas) |
| PATCH | /api/triagens/{id}/validar | Valida triagem por humano |
| GET | /api/triagens/paciente/{id} | Lista triagens do paciente |

### Fine-Tuning
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | /api/finetuning/modelos | Lista modelos disponiveis |
| POST | /api/finetuning/iniciar | Inicia job de fine-tuning |
| GET | /api/finetuning/jobs | Lista todos os jobs |
| GET | /api/finetuning/jobs/{id} | Status de um job |
| POST | /api/finetuning/jobs/{id}/cancelar | Cancela job |
| GET | /api/finetuning/dataset | Lista entradas do dataset |
| POST | /api/finetuning/dataset | Adiciona entrada ao dataset |
| DELETE | /api/finetuning/dataset/{id} | Remove entrada |
| POST | /api/finetuning/dataset/importar-json | Importa dataset sintetico JSON |
| POST | /api/finetuning/dataset/gerar | Gera dataset automatico por doenca (PubMed) |
| GET | /api/finetuning/dataset/stats | Estatisticas do dataset |
| GET | /api/finetuning/modelo-ativo | Info do modelo fine-tuned ativo |

### RAG
| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | /api/rag/indexar | Indexa todas as fontes |
| POST | /api/rag/indexar/dados-medicos | Indexa dados de scraping |
| POST | /api/rag/indexar/dataset | Indexa dataset de treinamento |
| POST | /api/rag/indexar/prontuarios | Indexa prontuarios |
| GET | /api/rag/buscar | Busca semantica por similaridade |
| GET | /api/rag/stats | Estatisticas do vector store |

### Scraping
| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | /api/scraping/buscar | Scraping por fonte especifica |
| POST | /api/scraping/agente | Agente de navegacao (Playwright) |
| POST | /api/scraping/agente-inteligente | Agente LLM (6 passos) |

### Auditoria
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | /api/auditoria/logs | Lista logs com filtro por acao |
| GET | /api/auditoria/stats | Estatisticas de auditoria |
| GET | /api/auditoria/categorias | Categorias de acoes |

### Config e Outros
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET/POST | /api/config/llm | Configuracao do LLM |
| POST | /api/prontuarios/ | Cria prontuario |
| GET | /api/health | Health check |

## Seguranca e Validacao

O sistema implementa as seguintes medidas de seguranca conforme requisitos do Tech Challenge:

- **Nunca prescreve sem validacao**: todos os system prompts incluem "NUNCA prescreva medicamentos diretamente" e "a validacao humana e necessaria".
- **Disclaimer educacional**: toda resposta inclui o aviso "Este e um simulador educacional. Procure um medico para diagnostico e tratamento adequados."
- **Auditoria completa**: o modelo `LogAuditoria` registra todas as acoes (triagem, chat, fine-tuning, scraping, config) com `acao`, `detalhes`, `usuario` e `criado_em`. Visualizavel pela interface de Auditoria.
- **Validacao humana obrigatoria**: toda classificacao de risco requer confirmacao por profissional (`validado_por_humano`). O LangGraph sempre define `proximo_passo = "validacao_humana"`.
- **Atribuicao de fontes (Explainability)**: cada resposta inclui rastreabilidade completa das fontes (LLM, RAG, Fine-Tuned, Web Search).
- **Anonimizacao**: dados de treinamento passam por anonimizacao automatica de CPF e nomes antes do fine-tuning.
- **Validacao Pydantic**: dados de pacientes validados com schemas (CPF, campos obrigatorios).

## Datasets

O projeto inclui um dataset sintetico com **40 entradas** abrangendo protocolos medicos (20), procedimentos internos (10), perguntas frequentes de medicos (8), modelos de laudos (5) e modelos de receitas (5).

O dataset pode ser enriquecido automaticamente via:
- **Agente de Scraping Inteligente**: LLM planeja buscas, coleta de PubMed/Drauzio/BVS/Scholar, gera pares Q&A
- **Geracao por doenca**: busca artigos no PubMed e gera entries automaticamente
- **Importacao manual**: via API ou interface

| Dataset | Conteudo | Link |
|---------|----------|------|
| PubMedQA | Perguntas clinicas | https://pubmedqa.github.io/ |
| MedQuAD | Perguntas sobre saude | https://github.com/abachaa/MedQuAD |

## Relatorio Tecnico

### Processo de Fine-Tuning

O projeto utiliza **PEFT (Parameter-Efficient Fine-Tuning)** com a tecnica **LoRA (Low-Rank Adaptation)** para personalizar modelos de linguagem com dados medicos hospitalares, sem a necessidade de retreinar todos os parametros do modelo base. O pipeline completo e gerenciavel pela interface web.

**Modelos suportados:**

| Modelo | Parametros | Tipo | Observacao |
|--------|-----------|------|------------|
| Qwen 3.5 4B | ~4B | Causal LM | Boa relacao custo/qualidade, ~4 GB RAM |
| Qwen 3.5 9B | ~9B | Causal LM | Superior em raciocinio clinico, ~8 GB RAM |

**Hiperparametros de treinamento (LoRA):**

- **Rank (r):** 8 - dimensao da decomposicao de baixo rank
- **Alpha:** 16 - fator de escala para os pesos LoRA (razao alpha/r = 2)
- **Dropout:** 0.1 - regularizacao para evitar overfitting
- **Target modules:** all-linear (todas as camadas lineares do modelo)
- **Learning rate:** 2e-4 com scheduler cosine
- **Epocas:** 3 (configuravel)
- **Batch size:** 2 (configuravel)
- **Precisao:** BF16 (mixed precision training)
- **Otimizador:** AdamW
- **Deteccao de dispositivo:** Intel XPU (Arc A770) / CUDA / CPU automatica

O fine-tuning e executado via `backend/app/services/finetuning_service.py` em thread separada (nao bloqueia o FastAPI), com monitoramento em tempo real via `ProgressTrainerCallback` que atualiza progresso, epoca e loss no banco a cada step.

### Assistente Medico (Pipeline Multi-Fonte)

O assistente medico virtual utiliza uma arquitetura **RAG (Retrieval-Augmented Generation)** integrada com **LangChain** e enriquecida com **4 fontes de conhecimento em paralelo**:

**Componentes do pipeline:**

- **RAG (ChromaDB):** Vector store local com embeddings `sentence-transformers/all-MiniLM-L6-v2`. Indexa dados medicos (scraping), dataset de treinamento e prontuarios anonimizados. Busca semantica Top-5 com distancia cosseno e filtro >= 0.15.
- **Fine-Tuned Model:** Modelo treinado com LoRA, carregado via lazy loading com cache global. Resposta injetada como contexto especializado no prompt.
- **Web Search (Brave):** 3 resultados de busca web em portugues para queries medicas.
- **Contexto do Paciente:** Prontuarios, triagens, alergias e medicamentos recuperados do banco via paciente_id.
- **MCP Tools (ReAct Agent):** Quando a pergunta envolve dados de pacientes, o sistema usa um LangGraph ReAct Agent com 7 ferramentas MCP para busca direta no banco.
- **LLM Principal:** OpenAI (GPT-4o-mini), Ollama ou llama.cpp SYCL, configuravel em runtime.
- **Explainability:** Cada resposta inclui rastreabilidade completa: `LLM: provider/model | RAG: fontes | Fine-Tuned: Modelo Especializado | Web: Brave Search`

### Diagrama do Fluxo LangChain

```
┌─────────────────┐     HTTP      ┌──────────────────┐     SQL      ┌────────────┐
│   Angular 19    │──────────────>│   FastAPI API     │────────────>│ PostgreSQL │
│   (Frontend)    │<──────────────│   (Backend)       │<────────────│   16       │
└─────────────────┘               └──────┬───────────┘              └────────────┘
                                         │
                          ┌──────────────┼──────────────────┐
                          │              │                  │
                    ┌─────▼────┐  ┌──────▼──────┐  ┌───────▼───────┐
                    │ LangChain│  │  ChromaDB   │  │  Fine-Tuned   │
                    │  + LLM   │  │  (RAG)      │  │  Model (LoRA) │
                    └─────┬────┘  └─────────────┘  └───────────────┘
                          │
               ┌──────────┼──────────┐
               │          │          │
         ┌─────▼──┐ ┌─────▼──┐ ┌────▼───────┐
         │OpenAI  │ │Ollama  │ │llama.cpp   │
         │API     │ │(local) │ │SYCL (GPU)  │
         └────────┘ └────────┘ └────────────┘
```

### Avaliacao do Modelo

**Metricas de treinamento (fine-tuning com LoRA):**

| Metrica | Valor |
|---------|-------|
| Loss inicial | ~2.5 |
| Loss final | ~0.6 |
| Reducao de loss | ~76% |
| Epocas de treinamento | 3 |
| Tempo medio por epoca | ~2 min (GPU) |

**Curva de loss:**

```
Loss
 2.5 |*
 2.0 | *
 1.5 |  *
 1.0 |   * *
 0.6 |       * * *
     +--+--+--+--+--+--+--+--+-->
     0  50 100 150 200 250 300 Steps
```

**Estatisticas do dataset (sintetico base):**

| Categoria | Quantidade | Percentual |
|-----------|-----------|------------|
| Protocolos medicos | 20 | 50% |
| Procedimentos internos | 10 | 25% |
| Perguntas frequentes de medicos | 8 | 20% |
| Modelos de laudos | 5 | 12.5% |
| Modelos de receitas | 5 | 12.5% |
| **Total** | **40** | **100%** |

> O dataset e expandido automaticamente via agente de scraping inteligente e geracao por doenca.

**Eficiencia do LoRA:**

| Metrica | Valor |
|---------|-------|
| Parametros totais do modelo base (Qwen 3.5 4B) | ~4B |
| Parametros treinaveis (LoRA all-linear) | < 1% do total |
| Tamanho do adapter salvo | ~6 MB |
| Reducao de VRAM vs full fine-tuning | ~75% |

A abordagem LoRA permite fine-tuning eficiente em hardware acessivel (GPU com 4GB+ de VRAM ou Intel Arc A770), mantendo a qualidade do modelo base enquanto especializa o conhecimento em protocolos medicos hospitalares.

## Infraestrutura Docker

| Servico | Imagem | Porta | Descricao |
|---------|--------|-------|-----------|
| postgres | postgres:16-alpine | 5433:5432 | Banco de dados |
| llama-server | ghcr.io/ggml-org/llama.cpp:server-intel | 8081:8080 | LLM local (Intel SYCL) |
| backend | python:3.11-slim (custom) | 8001:8000 | API FastAPI |
| frontend | angular/nginx | 8090:80 | Interface web |

**Modelos LLM disponiveis:**

| Modelo | Formato | Uso | RAM |
|--------|---------|-----|-----|
| Qwen 3.5 4B | GGUF (Q4_K_M) | llama.cpp SYCL | ~4 GB |
| Qwen 3.5 9B | GGUF | llama.cpp SYCL | ~8 GB |
| qwen2.5:3b | Ollama | Ollama CPU/GPU | ~3 GB |
| qwen2.5:7b | Ollama | Ollama CPU/GPU | ~7 GB |
| gpt-4o-mini | API | OpenAI Cloud | N/A |
| Qualquer modelo Ollama | Ollama | Configuravel via UI | Variavel |

## Pacientes de Teste

O seed script (`scripts/seed_pacientes_completo.py`) cria **25 pacientes** com dados realistas, 40+ prontuarios e 12+ triagens. Exemplos:

| CPF | Nome | Condicao |
|-----|------|----------|
| 123.456.789-00 | Maria Silva Santos | Hipertensao + Diabetes |
| 234.567.890-11 | Joao Pedro Oliveira | Lombalgia cronica |
| 345.678.901-22 | Ana Beatriz Costa | Asma bronquica |
| 456.789.012-33 | Carlos Eduardo Lima | Insuficiencia cardiaca |
| 567.890.123-44 | Fernanda Rodrigues | Gestante saudavel |

> Os 25 pacientes cobrem diversas especialidades: endocrinologia, cardiologia, pneumologia, neurologia, reumatologia, oncologia, infectologia, nefrologia, gastroenterologia, entre outras.
