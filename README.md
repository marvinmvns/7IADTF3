# MedAssist - Assistente Médico Virtual

**Tech Challenge Fase 3 - FIAP Pós Tech IA para Devs**

Assistente virtual médico com triagem inteligente, chat conversacional com IA, scraping de dados médicos, TTS/STT local (sem GPU) e interface responsiva.

## Arquitetura

O projeto segue o padrão **MVC (Model-View-Controller)** com separação clara de responsabilidades.

```
7IADTF3/
├── backend/                    # Python FastAPI (Model + Controller)
│   ├── app/
│   │   ├── models/             # Models - SQLAlchemy ORM
│   │   ├── controllers/        # Controllers - Rotas REST
│   │   ├── services/           # Services - Lógica de negócio
│   │   │   ├── llm/            # LangChain, LangGraph
│   │   │   ├── scraping/       # Scrapers + Agente de Navegação
│   │   │   └── tts/            # Piper TTS + Vosk STT
│   │   ├── schemas/            # Pydantic - Validação
│   │   ├── utils/              # Logger, auditoria
│   │   └── data/               # Dataset sintético
│   └── scripts/                # Fine-tuning, seed DB
├── frontend/                   # Angular 19 (View)
│   └── src/app/
│       ├── components/         # Chat, Triagem, Prontuário, Config, Scraping
│       ├── services/           # API Service
│       └── models/             # TypeScript interfaces
├── docker-compose.yml          # Orquestração completa
└── setup.sh                    # Script de instalação
```

## Tecnologias

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Python + FastAPI | 3.11 / 0.115 |
| Frontend | Angular | 19 |
| Banco de Dados | PostgreSQL | 16 |
| ORM | SQLAlchemy (async) | 2.0 |
| LLM | LangChain + LangGraph | 0.3 / 0.2 |
| TTS | Piper (local, sem GPU) | 1.2 |
| STT | Vosk (local, sem GPU) | 0.3 |
| Scraping | BeautifulSoup + Playwright | 4.12 / 1.47 |
| Container | Docker + Docker Compose | - |

## Funcionalidades

### Chat Conversacional com IA
Interface de chat com suporte a texto e voz. Três modos de conversa: geral, triagem e consulta médica. Cada resposta inclui a fonte da informação (explainability). Suporte a TTS (texto para voz) e STT (voz para texto) com modelos locais que rodam em CPU.

### Triagem Inteligente (Manchester)
Classificação de risco automatizada baseada no Protocolo Manchester com 5 níveis de cores. O sistema coleta sintomas e sinais vitais, classifica o risco e gera orientações via IA. Toda classificação requer validação humana antes de ser efetivada.

### Prontuário por CPF
Tela de busca por CPF que retorna a ficha completa do paciente: dados pessoais, histórico de consultas, medicamentos, alergias, triagens anteriores e conversas com a IA.

### Scraping de Dados Médicos
Sete scrapers inteligentes para sites de referência médica:

| Fonte | Tipo | URL |
|-------|------|-----|
| PubMed | Artigos científicos | pubmed.ncbi.nlm.nih.gov |
| MedlinePlus | Informações de saúde | medlineplus.gov |
| BVS/BIREME | Literatura médica | pesquisa.bvsalud.org |
| Drauzio Varella | Divulgação (PT-BR) | drauziovarella.uol.com.br |
| Mayo Clinic | Referência médica | mayoclinic.org |
| DataSUS | Dados públicos BR | datasus.saude.gov.br |
| OpenFDA | Medicamentos | api.fda.gov |

### Agente de Navegação
Agente autônomo que navega em múltiplos sites médicos usando Playwright, coleta informações e segue links relevantes automaticamente. Possui fallback com httpx para ambientes sem Playwright.

### Configuração de LLM
Tela para parametrizar o modelo de linguagem em tempo real. Suporta OpenAI (GPT-4o-mini, GPT-4, etc.) e Ollama (Llama3, Mistral, etc.) com ajuste de temperatura e max tokens.

### Pipeline de Fine-Tuning
Script de fine-tuning com PEFT/LoRA para personalizar LLMs com dados médicos do hospital. Inclui anonimização de dados sensíveis e dataset sintético com 20 exemplos de protocolos clínicos.

## Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/marvinmvns/7IADTF3.git
cd 7IADTF3

# Configure a API Key (opcional para OpenAI)
cp backend/.env.example backend/.env
# Edite backend/.env e adicione sua OPENAI_API_KEY

# Execute o setup
chmod +x setup.sh
./setup.sh
```

Acesse: **http://localhost** (frontend) | **http://localhost:8000/docs** (API)

## Uso com Ollama (LLM Local)

```bash
# Inicia com perfil local-llm
docker compose --profile local-llm up -d

# Baixa modelo Llama3
docker compose exec ollama ollama pull llama3

# Na tela de Configuração, selecione:
# Provider: Ollama | Modelo: llama3
```

## Fluxo LangGraph - Triagem

```
[Coletar Sintomas] → [Classificar Risco] → {Urgente?}
                                              ├─ Sim → [Gerar Alerta] → [Verificar Exames] → [Orientação] → FIM
                                              └─ Não → [Verificar Exames] → [Orientação] → FIM
```

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | /api/pacientes/cpf/{cpf} | Busca paciente por CPF |
| GET | /api/pacientes/cpf/{cpf}/ficha | Ficha completa do paciente |
| POST | /api/pacientes/ | Cadastra paciente |
| POST | /api/prontuarios/ | Cria prontuário |
| POST | /api/triagens/ | Realiza triagem com IA |
| POST | /api/chat/mensagem | Envia mensagem ao chat |
| POST | /api/chat/voz-para-texto | STT (áudio para texto) |
| POST | /api/chat/texto-para-voz | TTS (texto para áudio) |
| GET/POST | /api/config/llm | Configuração do LLM |
| POST | /api/scraping/buscar | Scraping por fonte |
| POST | /api/scraping/agente | Agente de navegação |
| GET | /api/health | Health check |

## Segurança e Validação

O sistema implementa as seguintes medidas de segurança conforme requisitos do Tech Challenge:

O assistente nunca prescreve medicamentos diretamente, sempre indicando que a validação humana é necessária. Todas as ações são registradas em log de auditoria para rastreamento. As respostas da IA incluem a fonte da informação utilizada (explainability). Os dados de pacientes são validados com Pydantic (CPF, campos obrigatórios). O dataset de fine-tuning passa por anonimização automática de dados sensíveis.

## Datasets

O projeto inclui um dataset sintético com 20 exemplos de protocolos médicos hospitalares. Para datasets reais, consulte:

| Dataset | Conteúdo | Link |
|---------|----------|------|
| PubMedQA | Perguntas clínicas | https://pubmedqa.github.io/ |
| MedQuAD | Perguntas sobre saúde | https://github.com/abachaa/MedQuAD |

## Pacientes de Teste

| CPF | Nome | Condição |
|-----|------|----------|
| 123.456.789-00 | Maria Silva Santos | Hipertensão + Diabetes |
| 234.567.890-11 | João Pedro Oliveira | Lombalgia crônica |
| 345.678.901-22 | Ana Beatriz Costa | Asma brônquica |
| 456.789.012-33 | Carlos Eduardo Lima | Insuficiência cardíaca |
| 567.890.123-44 | Fernanda Rodrigues | - |
