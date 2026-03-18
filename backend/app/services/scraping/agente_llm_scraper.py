"""Agente de Scraping Inteligente - usa LLM para planejar, navegar e extrair dados médicos."""
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import DadoMedico, DatasetEntry

logger = logging.getLogger("medassist.agente_scraper")

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


@dataclass
class DadoColetado:
    titulo: str
    conteudo_preview: str
    url: str
    fonte: str


@dataclass
class QAPar:
    pergunta: str
    resposta_preview: str
    fonte: str


@dataclass
class PassoAgente:
    passo: int
    acao: str
    fonte: str
    status: str = "pendente"
    resultado: str = ""
    dados_coletados: int = 0
    dataset_gerado: int = 0
    itens: list[DadoColetado] = field(default_factory=list)
    qa_gerados: list[QAPar] = field(default_factory=list)


@dataclass
class ResultadoAgente:
    tema: str
    passos: list[PassoAgente] = field(default_factory=list)
    perguntas_planejadas: list[str] = field(default_factory=list)
    total_dados: int = 0
    total_dataset: int = 0
    concluido: bool = False


PROMPT_PLANEJAR = """Você é um agente de pesquisa médica. Dado o tema "{tema}", gere uma lista de 5 perguntas específicas em português que um médico faria sobre este tema. Cada pergunta deve cobrir um aspecto diferente:
1. Definição/fisiopatologia
2. Sintomas e diagnóstico
3. Tratamento e medicamentos
4. Complicações e prognóstico
5. Prevenção e epidemiologia

Responda APENAS com as 5 perguntas, uma por linha, sem numeração ou marcadores."""

PROMPT_RESUMIR = """Resuma o seguinte texto médico em português, de forma clara e objetiva para uso em um dataset de treinamento de IA médica. Máximo 300 palavras.

Texto: {texto}

Resumo:"""

PROMPT_GERAR_QA = """Com base no seguinte conteúdo médico sobre "{tema}", gere 3 pares de pergunta e resposta em português para treinar uma IA médica.

Conteúdo: {conteudo}

Formato (um par por bloco, separados por linha em branco):
P: [pergunta]
R: [resposta]"""


async def _chamar_llm(db: AsyncSession, prompt: str) -> str:
    """Chama o LLM configurado para gerar texto."""
    try:
        from app.services.llm.langchain_service import LangChainService
        service = LangChainService(db)
        llm = await service._get_llm()
        resp = await llm.ainvoke(prompt)
        return resp.content.strip()
    except Exception as e:
        logger.warning(f"LLM indisponível: {e}")
        return ""


async def _buscar_pubmed(termo: str, max_results: int = 5) -> list[dict]:
    """Busca artigos no PubMed."""
    resultados = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(PUBMED_SEARCH, params={
                "db": "pubmed", "term": termo, "retmax": max_results,
                "retmode": "json", "sort": "relevance",
            })
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            resp = await client.get(PUBMED_FETCH, params={
                "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.find_all("pubmedarticle"):
                titulo = article.find("articletitle")
                abstract = article.find("abstracttext")
                pmid = article.find("pmid")
                if abstract and len(abstract.text) > 100:
                    resultados.append({
                        "titulo": titulo.text if titulo else "Sem título",
                        "conteudo": abstract.text,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/" if pmid else "",
                        "fonte": "pubmed",
                    })
    except Exception as e:
        logger.warning(f"PubMed falhou: {e}")
    return resultados


async def _buscar_url(url: str) -> dict | None:
    """Faz scraping de uma URL genérica."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "MedAssist-Bot/1.0"})
            if resp.status_code != 200:
                return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        titulo = soup.title.text.strip() if soup.title else ""
        main = soup.find("main") or soup.find("article") or soup.body
        conteudo = main.get_text(separator=" ", strip=True)[:5000] if main else ""
        if len(conteudo) < 100:
            return None
        return {"titulo": titulo, "conteudo": conteudo, "url": url, "fonte": "web"}
    except Exception:
        return None


async def _buscar_google_scholar(termo: str) -> list[str]:
    """Extrai URLs de resultados do Google Scholar."""
    urls = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                "https://scholar.google.com/scholar",
                params={"q": termo, "hl": "pt-BR"},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.select("h3.gs_rt a")[:3]:
                href = link.get("href", "")
                if href.startswith("http"):
                    urls.append(href)
    except Exception:
        pass
    return urls


def _parse_qa_pairs(texto: str, tema: str) -> list[tuple[str, str]]:
    """Parseia pares P/R do output do LLM."""
    pares = []
    linhas = texto.strip().split("\n")
    pergunta = ""
    for linha in linhas:
        linha = linha.strip()
        if linha.startswith("P:") or linha.startswith("P :"):
            pergunta = linha.split(":", 1)[1].strip()
        elif linha.startswith("R:") or linha.startswith("R :"):
            resposta = linha.split(":", 1)[1].strip()
            if pergunta and resposta:
                pares.append((pergunta, resposta))
                pergunta = ""
    return pares


async def executar_agente_inteligente(db: AsyncSession, tema: str) -> ResultadoAgente:
    """Executa o agente de scraping inteligente completo."""
    resultado = ResultadoAgente(tema=tema)

    # Passo 1: LLM planeja as buscas
    passo1 = PassoAgente(passo=1, acao="Planejando pesquisa com IA", fonte="LLM")
    resultado.passos.append(passo1)
    perguntas_raw = await _chamar_llm(db, PROMPT_PLANEJAR.format(tema=tema))
    perguntas = [p.strip() for p in perguntas_raw.split("\n") if p.strip() and len(p.strip()) > 10][:5]
    if not perguntas:
        perguntas = [
            f"O que é {tema}?",
            f"Quais os sintomas de {tema}?",
            f"Qual o tratamento para {tema}?",
            f"Quais as complicações de {tema}?",
            f"Como prevenir {tema}?",
        ]
    passo1.status = "concluido"
    passo1.resultado = f"{len(perguntas)} perguntas geradas"
    resultado.perguntas_planejadas = perguntas

    # Passo 2: Busca no PubMed
    passo2 = PassoAgente(passo=2, acao="Buscando artigos no PubMed", fonte="PubMed")
    resultado.passos.append(passo2)
    artigos = await _buscar_pubmed(tema, max_results=5)
    passo2.status = "concluido"
    passo2.dados_coletados = len(artigos)
    passo2.resultado = f"{len(artigos)} artigos encontrados"
    passo2.itens = [DadoColetado(
        titulo=a["titulo"][:100], conteudo_preview=a["conteudo"][:200],
        url=a.get("url", ""), fonte=a["fonte"]
    ) for a in artigos]

    # Passo 3: Busca em fontes brasileiras
    passo3 = PassoAgente(passo=3, acao="Buscando em fontes brasileiras", fonte="Drauzio/BVS")
    resultado.passos.append(passo3)
    fontes_br = []
    urls_br = [
        f"https://drauziovarella.uol.com.br/?s={tema}",
        f"https://pesquisa.bvsalud.org/portal/?q={tema}&lang=pt",
    ]
    for url in urls_br:
        dado = await _buscar_url(url)
        if dado:
            fontes_br.append(dado)
    passo3.status = "concluido"
    passo3.dados_coletados = len(fontes_br)
    passo3.resultado = f"{len(fontes_br)} fontes brasileiras"
    passo3.itens = [DadoColetado(
        titulo=d["titulo"][:100], conteudo_preview=d["conteudo"][:200],
        url=d.get("url", ""), fonte=d["fonte"]
    ) for d in fontes_br]

    # Passo 4: Busca acadêmica
    passo4 = PassoAgente(passo=4, acao="Buscando artigos acadêmicos", fonte="Google Scholar")
    resultado.passos.append(passo4)
    urls_scholar = await _buscar_google_scholar(tema)
    artigos_scholar = []
    for url in urls_scholar:
        dado = await _buscar_url(url)
        if dado:
            artigos_scholar.append(dado)
    passo4.status = "concluido"
    passo4.dados_coletados = len(artigos_scholar)
    passo4.resultado = f"{len(artigos_scholar)} artigos acadêmicos"
    passo4.itens = [DadoColetado(
        titulo=d["titulo"][:100], conteudo_preview=d["conteudo"][:200],
        url=d.get("url", ""), fonte=d["fonte"]
    ) for d in artigos_scholar]

    # Consolidar todos os dados coletados
    todos_dados = artigos + fontes_br + artigos_scholar

    # Passo 5: Salvar dados médicos no banco
    passo5 = PassoAgente(passo=5, acao="Salvando dados coletados", fonte="Banco de Dados")
    resultado.passos.append(passo5)
    for dado in todos_dados:
        obj = DadoMedico(
            fonte=dado["fonte"],
            titulo=dado["titulo"][:500],
            conteudo=dado["conteudo"][:5000],
            url=dado.get("url", ""),
            categoria=f"agente_{tema}",
        )
        db.add(obj)
    await db.commit()
    passo5.status = "concluido"
    passo5.dados_coletados = len(todos_dados)
    passo5.resultado = f"{len(todos_dados)} registros salvos"
    resultado.total_dados = len(todos_dados)

    # Passo 6: LLM gera pares Q&A para o dataset
    passo6 = PassoAgente(passo=6, acao="Gerando dataset com IA", fonte="LLM + Dados")
    resultado.passos.append(passo6)
    total_qa = 0

    for dado in todos_dados[:8]:
        conteudo = dado["conteudo"][:2000]
        qa_raw = await _chamar_llm(db, PROMPT_GERAR_QA.format(tema=tema, conteudo=conteudo))
        pares = _parse_qa_pairs(qa_raw, tema)

        for pergunta, resposta in pares:
            passo6.qa_gerados.append(QAPar(
                pergunta=pergunta, resposta_preview=resposta[:150],
                fonte=dado["fonte"],
            ))
            entry = DatasetEntry(
                pergunta=pergunta,
                contexto=f"Fonte: {dado['fonte']} - {dado['titulo'][:200]}",
                resposta=resposta,
                categoria=f"agente_llm_{dado['fonte']}",
            )
            db.add(entry)
            total_qa += 1

    # Adicionar perguntas planejadas pelo LLM como entries do dataset
    for i, pergunta in enumerate(perguntas):
        if i < len(todos_dados):
            entry = DatasetEntry(
                pergunta=pergunta,
                contexto=f"Pesquisa: {tema}",
                resposta=todos_dados[i]["conteudo"][:1500],
                categoria="agente_llm_planejado",
            )
            db.add(entry)
            total_qa += 1

    await db.commit()
    passo6.status = "concluido"
    passo6.dataset_gerado = total_qa
    passo6.resultado = f"{total_qa} pares Q&A gerados"
    resultado.total_dataset = total_qa
    resultado.concluido = True

    return resultado
