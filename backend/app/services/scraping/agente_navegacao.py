"""Agente de Navegação Inteligente - usa Playwright para scraping dinâmico."""
import asyncio
from dataclasses import dataclass


@dataclass
class PaginaColetada:
    url: str
    titulo: str
    conteudo: str
    links_relevantes: list[str]


class AgenteNavegacao:
    """Agente que navega autonomamente em sites médicos buscando informações."""

    SITES_MEDICOS = [
        {"nome": "PubMed", "url": "https://pubmed.ncbi.nlm.nih.gov/?term={termo}"},
        {"nome": "MedlinePlus", "url": "https://medlineplus.gov/search.html?query={termo}"},
        {"nome": "BVS", "url": "https://pesquisa.bvsalud.org/portal/?q={termo}&lang=pt"},
        {"nome": "Drauzio", "url": "https://drauziovarella.uol.com.br/?s={termo}"},
        {"nome": "Mayo Clinic", "url": "https://www.mayoclinic.org/search/search-results?q={termo}"},
        {"nome": "WHO", "url": "https://search.who.int/search?q={termo}"},
        {"nome": "Fiocruz", "url": "https://portal.fiocruz.br/search/conteudo/{termo}"},
    ]

    def __init__(self, max_paginas: int = 20, timeout: int = 15000):
        self.max_paginas = max_paginas
        self.timeout = timeout
        self.paginas_coletadas: list[PaginaColetada] = []

    async def navegar(self, termo: str) -> list[PaginaColetada]:
        """Navega em múltiplos sites médicos buscando informações sobre o termo."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="MedAssist-Academic-Bot/1.0",
                    viewport={"width": 1280, "height": 720},
                )

                tarefas = []
                for site in self.SITES_MEDICOS:
                    url = site["url"].format(termo=termo)
                    tarefas.append(self._coletar_pagina(context, url, site["nome"]))

                resultados = await asyncio.gather(*tarefas, return_exceptions=True)

                for r in resultados:
                    if isinstance(r, PaginaColetada):
                        self.paginas_coletadas.append(r)

                # Fase 2: navegar em links relevantes encontrados
                links_para_visitar = []
                for pagina in self.paginas_coletadas:
                    links_para_visitar.extend(pagina.links_relevantes[:2])

                for link in links_para_visitar[:self.max_paginas - len(self.paginas_coletadas)]:
                    try:
                        resultado = await self._coletar_pagina(context, link, "link_secundario")
                        if resultado:
                            self.paginas_coletadas.append(resultado)
                    except Exception:
                        continue

                await browser.close()

        except (ImportError, Exception):
            # Fallback sem Playwright ou se browser falhar: usar httpx
            return await self._fallback_httpx(termo)

        return self.paginas_coletadas

    async def _coletar_pagina(self, context, url: str, fonte: str) -> PaginaColetada | None:
        """Coleta conteúdo de uma página específica."""
        try:
            page = await context.new_page()
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

            titulo = await page.title()
            # Extrai texto principal
            conteudo = await page.evaluate("""
                () => {
                    const el = document.querySelector('main, article, .content, #content, .results');
                    return el ? el.innerText.substring(0, 5000) : document.body.innerText.substring(0, 3000);
                }
            """)
            # Coleta links relevantes
            links = await page.evaluate("""
                () => {
                    const anchors = document.querySelectorAll('a[href]');
                    return Array.from(anchors)
                        .map(a => a.href)
                        .filter(h => h.startsWith('http') && !h.includes('login') && !h.includes('signup'))
                        .slice(0, 5);
                }
            """)
            await page.close()

            return PaginaColetada(
                url=url, titulo=titulo,
                conteudo=conteudo[:5000], links_relevantes=links,
            )
        except Exception:
            return None

    async def _fallback_httpx(self, termo: str) -> list[PaginaColetada]:
        """Fallback usando httpx quando Playwright não está disponível."""
        import httpx
        from bs4 import BeautifulSoup

        resultados = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for site in self.SITES_MEDICOS[:4]:
                try:
                    url = site["url"].format(termo=termo)
                    resp = await client.get(url, headers={
                        "User-Agent": "MedAssist-Academic-Bot/1.0"
                    })
                    soup = BeautifulSoup(resp.text, "html.parser")
                    titulo = soup.title.text if soup.title else site["nome"]
                    main = soup.find("main") or soup.find("article") or soup.body
                    conteudo = main.get_text(separator=" ", strip=True)[:3000] if main else ""
                    links = [a["href"] for a in soup.find_all("a", href=True)[:5]
                             if a["href"].startswith("http")]
                    resultados.append(PaginaColetada(
                        url=url, titulo=titulo,
                        conteudo=conteudo, links_relevantes=links,
                    ))
                except Exception:
                    continue
        return resultados
