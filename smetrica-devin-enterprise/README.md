# Smetrica - Devin Enterprise Analytics

Este repositório contém um conjunto de scripts Python e um framework metodológico completo para extrair, processar e analisar métricas de uso, eficiência e ROI do **Devin Enterprise**.

O objetivo é fornecer evidências objetivas e auditáveis sobre o impacto do Devin na produtividade da engenharia de software, atendendo a requisitos de governança, finanças e liderança executiva.

## 📂 Estrutura do Projeto

```text
smetrica-devin-enterprise/
├── config/
│   └── settings.py              # Configurações centrais e variáveis de ambiente
├── docs/
│   └── FRAMEWORK_METRICAS.md    # Documentação completa do framework (Visão Executiva e Técnica)
├── scripts/
│   ├── api_client.py            # Cliente HTTP base com retry, rate limit e paginação
│   ├── extract_members_orgs.py  # Extração de dimensões (usuários e organizações)
│   ├── extract_usage_metrics.py # Extração de métricas de adoção (DAU/WAU/MAU, PRs)
│   ├── extract_sessions.py      # Extração detalhada de sessões e cálculo de duração
│   ├── extract_consumption.py   # Extração de consumo de ACUs e billing cycles
│   ├── extract_audit_logs.py    # Extração de logs de auditoria para governança
│   ├── calculate_metrics.py     # Cálculo de indicadores derivados (ROI, Score de Maturidade)
│   └── run_all.py               # Orquestrador da pipeline completa
├── .env.example                 # Exemplo de variáveis de ambiente
└── requirements.txt             # Dependências do projeto
```

## 🚀 Como Começar

### 1. Pré-requisitos
- Python 3.8+
- Chave de API do Devin Enterprise (Service User `cog_*` para v3 ou Personal API Key `apk_user_*` para v2).

### 2. Instalação

Clone o repositório e instale as dependências:

```bash
git clone <url-do-repositorio>
cd smetrica-devin-enterprise
pip install -r requirements.txt
```

### 3. Configuração

Copie o arquivo de exemplo e configure suas variáveis de ambiente:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e insira sua `DEVIN_API_KEY`. Você também pode ajustar o período de coleta (`DEVIN_DAYS_BACK`) e premissas de custo para o cálculo de ROI (`DEV_HOUR_COST`, `AVG_TASK_HOURS`).

Para carregar as variáveis no terminal (Linux/macOS):
```bash
export $(grep -v '^#' .env | xargs)
```

### 4. Execução

Você pode executar a pipeline completa através do orquestrador:

```bash
python3 scripts/run_all.py
```

Ou executar scripts individuais conforme a necessidade:

```bash
python3 scripts/extract_sessions.py
python3 scripts/calculate_metrics.py --dev-hour-cost 100.0 --avg-task-hours 5.0
```

## 📊 Saídas (Outputs)

Os scripts gerarão arquivos JSON e CSV no diretório `output/` (criado automaticamente). Estes arquivos estão prontos para serem ingeridos por ferramentas de BI (Power BI, Tableau, Metabase) ou Data Warehouses.

Principais arquivos gerados:
- `enterprise_sessions.csv`: Tabela detalhada de todas as sessões para análise granular.
- `derived_metrics.json`: Scores calculados de Adoção e Eficiência.
- `roi_analysis.json`: Análise financeira de custo evitado vs custo do Devin.
- `maturity_scorecard.json`: Score consolidado de maturidade do uso da ferramenta.

## 📖 Documentação do Framework

Para entender a metodologia por trás das métricas, como evitar distorções (gaming), como medir o impacto em tarefas de obsolescência e como apresentar os resultados para a diretoria, leia o documento completo:

👉 **[Framework de Métricas e Instrumentação (docs/FRAMEWORK_METRICAS.md)](docs/FRAMEWORK_METRICAS.md)**
