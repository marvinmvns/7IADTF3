"""Serviço de Scraping - orquestra scrapers e agente de navegação."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import DadoMedico
from app.services.scraping.scrapers import SCRAPERS
from app.services.scraping.agente_navegacao import AgenteNavegacao


class ScrapingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar(self, fonte: str, termo: str, max_resultados: int = 10) -> list[DadoMedico]:
        """Busca dados usando o scraper específico e salva no banco."""
        scraper_cls = SCRAPERS.get(fonte)
        if not scraper_cls:
            fontes = ", ".join(SCRAPERS.keys())
            raise ValueError(f"Fonte '{fonte}' não suportada. Use: {fontes}")

        scraper = scraper_cls()
        resultados = await scraper.buscar(termo, max_resultados)

        dados_salvos = []
        for r in resultados:
            dado = DadoMedico(
                fonte=r.fonte,
                titulo=r.titulo,
                conteudo=r.conteudo,
                url=r.url,
                categoria=r.categoria,
            )
            self.db.add(dado)
            dados_salvos.append(dado)

        await self.db.commit()
        for d in dados_salvos:
            await self.db.refresh(d)
        return dados_salvos

    async def buscar_todas_fontes(self, termo: str, max_por_fonte: int = 5) -> list[DadoMedico]:
        """Busca em todas as fontes disponíveis."""
        todos = []
        for fonte in SCRAPERS:
            try:
                dados = await self.buscar(fonte, termo, max_por_fonte)
                todos.extend(dados)
            except Exception:
                continue
        return todos

    async def agente_navegacao(self, termo: str) -> dict:
        """Executa agente de navegação inteligente."""
        agente = AgenteNavegacao(max_paginas=15)
        paginas = await agente.navegar(termo)

        # Salva resultados no banco
        for p in paginas:
            dado = DadoMedico(
                fonte="agente_navegacao",
                titulo=p.titulo,
                conteudo=p.conteudo[:5000],
                url=p.url,
                categoria="navegacao_automatica",
            )
            self.db.add(dado)
        await self.db.commit()

        return {
            "termo": termo,
            "paginas_coletadas": len(paginas),
            "resultados": [
                {"titulo": p.titulo, "url": p.url, "conteudo_preview": p.conteudo[:200]}
                for p in paginas
            ],
        }

    async def listar(self, fonte: str = None, skip: int = 0, limit: int = 50):
        stmt = select(DadoMedico)
        if fonte:
            stmt = stmt.where(DadoMedico.fonte == fonte)
        stmt = stmt.order_by(DadoMedico.coletado_em.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
