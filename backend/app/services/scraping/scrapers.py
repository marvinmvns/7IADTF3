"""Scrapers inteligentes para sites médicos de referência."""
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ResultadoScraping:
    titulo: str
    conteudo: str
    url: str
    fonte: str
    categoria: str = ""


class BaseScraper(ABC):
    """Classe base para todos os scrapers."""
    HEADERS = {
        "User-Agent": "MedAssist-Academic-Bot/1.0 (Projeto Academico FIAP)",
        "Accept": "text/html,application/json",
    }

    @abstractmethod
    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        pass


class PubMedScraper(BaseScraper):
    """Scraper para PubMed - artigos e pesquisas médicas."""
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30) as client:
            # Busca IDs dos artigos
            resp = await client.get(f"{self.BASE_URL}/esearch.fcgi", params={
                "db": "pubmed", "term": termo, "retmax": max_resultados,
                "retmode": "json", "sort": "relevance",
            })
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            # Busca detalhes dos artigos
            resp = await client.get(f"{self.BASE_URL}/efetch.fcgi", params={
                "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for article in soup.find_all("pubmedarticle"):
                titulo = article.find("articletitle")
                abstract = article.find("abstracttext")
                pmid = article.find("pmid")
                resultados.append(ResultadoScraping(
                    titulo=titulo.text if titulo else "Sem título",
                    conteudo=abstract.text if abstract else "Sem resumo",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/" if pmid else "",
                    fonte="pubmed",
                    categoria="artigo_cientifico",
                ))
            return resultados


class MedlinePlusScraper(BaseScraper):
    """Scraper para MedlinePlus - informações de saúde para pacientes."""
    BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL, params={
                "db": "healthTopics", "term": termo,
                "retmax": max_resultados, "rettype": "brief",
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for doc in soup.find_all("document")[:max_resultados]:
                titulo = doc.find("content", {"name": "title"})
                snippet = doc.find("content", {"name": "snippet"})
                url = doc.get("url", "")
                resultados.append(ResultadoScraping(
                    titulo=titulo.text if titulo else "Sem título",
                    conteudo=snippet.text if snippet else "",
                    url=url,
                    fonte="medlineplus",
                    categoria="informacao_saude",
                ))
            return resultados


class BVSScraper(BaseScraper):
    """Scraper para BVS/BIREME - Biblioteca Virtual em Saúde."""
    BASE_URL = "https://pesquisa.bvsalud.org/portal/"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30, headers=self.HEADERS) as client:
            resp = await client.get(self.BASE_URL, params={
                "q": termo, "lang": "pt", "count": max_resultados,
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for item in soup.select(".result")[:max_resultados]:
                titulo_el = item.select_one(".title a")
                resumo_el = item.select_one(".abstract")
                resultados.append(ResultadoScraping(
                    titulo=titulo_el.text.strip() if titulo_el else "Sem título",
                    conteudo=resumo_el.text.strip() if resumo_el else "",
                    url=titulo_el["href"] if titulo_el and titulo_el.get("href") else "",
                    fonte="bvs",
                    categoria="literatura_medica",
                ))
            return resultados


class DrauzioScraper(BaseScraper):
    """Scraper para Drauzio Varella - informações de saúde em PT-BR."""
    BASE_URL = "https://drauziovarella.uol.com.br"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(f"{self.BASE_URL}/", params={"s": termo})
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for item in soup.select("article")[:max_resultados]:
                titulo_el = item.select_one("h2 a, h3 a")
                resumo_el = item.select_one("p")
                link = titulo_el["href"] if titulo_el and titulo_el.get("href") else ""
                resultados.append(ResultadoScraping(
                    titulo=titulo_el.text.strip() if titulo_el else "Sem título",
                    conteudo=resumo_el.text.strip() if resumo_el else "",
                    url=link,
                    fonte="drauzio",
                    categoria="divulgacao_saude",
                ))
            return resultados


class MayoClinicScraper(BaseScraper):
    """Scraper para Mayo Clinic - referência médica internacional."""
    BASE_URL = "https://www.mayoclinic.org/search/search-results"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.BASE_URL, params={"q": termo})
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for item in soup.select(".aem-search-result, .result")[:max_resultados]:
                titulo_el = item.select_one("a")
                resumo_el = item.select_one("p, .description")
                link = titulo_el["href"] if titulo_el and titulo_el.get("href") else ""
                if link and not link.startswith("http"):
                    link = f"https://www.mayoclinic.org{link}"
                resultados.append(ResultadoScraping(
                    titulo=titulo_el.text.strip() if titulo_el else "Sem título",
                    conteudo=resumo_el.text.strip() if resumo_el else "",
                    url=link,
                    fonte="mayo_clinic",
                    categoria="referencia_medica",
                ))
            return resultados


class DataSUSScraper(BaseScraper):
    """Scraper para DataSUS - dados de saúde pública brasileira."""
    BASE_URL = "https://datasus.saude.gov.br"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30, headers=self.HEADERS, follow_redirects=True) as client:
            resp = await client.get(f"{self.BASE_URL}/informacoes-de-saude-tabnet/", params={"s": termo})
            soup = BeautifulSoup(resp.text, "html.parser")
            resultados = []
            for item in soup.select("a[href*='tabnet'], .content-item")[:max_resultados]:
                resultados.append(ResultadoScraping(
                    titulo=item.text.strip(),
                    conteudo=f"Dados do DataSUS sobre: {termo}",
                    url=item.get("href", self.BASE_URL),
                    fonte="datasus",
                    categoria="dados_publicos",
                ))
            return resultados


class OpenFDAScraper(BaseScraper):
    """Scraper para OpenFDA - dados de medicamentos e eventos adversos."""
    BASE_URL = "https://api.fda.gov"

    async def buscar(self, termo: str, max_resultados: int = 10) -> list[ResultadoScraping]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.BASE_URL}/drug/label.json", params={
                "search": f'openfda.generic_name:"{termo}"',
                "limit": min(max_resultados, 10),
            })
            if resp.status_code != 200:
                return []
            data = resp.json()
            resultados = []
            for item in data.get("results", []):
                nome = item.get("openfda", {}).get("brand_name", ["Desconhecido"])[0]
                indicacoes = item.get("indications_and_usage", [""])[0][:500]
                resultados.append(ResultadoScraping(
                    titulo=f"Medicamento: {nome}",
                    conteudo=indicacoes,
                    url="https://open.fda.gov",
                    fonte="openfda",
                    categoria="medicamento",
                ))
            return resultados


# Registro de scrapers disponíveis
SCRAPERS = {
    "pubmed": PubMedScraper,
    "medlineplus": MedlinePlusScraper,
    "bvs": BVSScraper,
    "drauzio": DrauzioScraper,
    "mayo_clinic": MayoClinicScraper,
    "datasus": DataSUSScraper,
    "openfda": OpenFDAScraper,
}
