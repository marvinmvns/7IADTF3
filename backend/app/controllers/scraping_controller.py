"""Controller de Scraping - busca de dados médicos."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import ScrapingRequest, DadoMedicoOut
from app.services.scraping.scraping_service import ScrapingService
from app.models.models import DadoMedico, DatasetEntry
from app.utils.logger import registrar_log

logger = logging.getLogger("medassist")
router = APIRouter(prefix="/scraping", tags=["Scraping"])


@router.post("/buscar", response_model=list[DadoMedicoOut])
async def buscar_dados(req: ScrapingRequest, db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    try:
        dados = await service.buscar(req.fonte, req.termo, req.max_resultados)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Scraping falhou ({req.fonte}): {e}")
        raise HTTPException(502, f"Erro ao acessar fonte '{req.fonte}': {type(e).__name__}")
    await registrar_log(db, "scraping", f"Fonte: {req.fonte}, Termo: {req.termo}, Resultados: {len(dados)}")
    return dados


@router.get("/dados", response_model=list[DadoMedicoOut])
async def listar_dados(fonte: str = None, skip: int = 0, limit: int = 50,
                       db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    return await service.listar(fonte, skip, limit)


@router.post("/buscar-todas", response_model=list[DadoMedicoOut])
async def buscar_todas_fontes(termo: str, db: AsyncSession = Depends(get_db)):
    """Busca em todas as fontes disponíveis simultaneamente."""
    service = ScrapingService(db)
    try:
        resultados = await service.buscar_todas_fontes(termo, max_por_fonte=5)
    except Exception as e:
        logger.error(f"Scraping todas fontes falhou: {e}")
        raise HTTPException(502, f"Erro ao buscar em todas as fontes: {type(e).__name__}")
    await registrar_log(db, "scraping_todas", f"Termo: {termo}, Total: {len(resultados)}")
    return resultados


@router.post("/agente")
async def executar_agente(termo: str, db: AsyncSession = Depends(get_db)):
    service = ScrapingService(db)
    try:
        resultado = await service.agente_navegacao(termo)
    except Exception as e:
        logger.error(f"Agente falhou: {e}")
        raise HTTPException(502, f"Erro no agente de navegação: {type(e).__name__}")
    await registrar_log(db, "agente_navegacao", f"Termo: {termo}, Páginas: {resultado.get('paginas_coletadas', 0)}")
    return resultado


@router.post("/enviar-para-dataset")
async def enviar_para_dataset(termo: str, db: AsyncSession = Depends(get_db)):
    """Converte dados coletados pelo scraping em entradas do dataset de fine-tuning."""
    # Busca dados médicos coletados que contenham o termo
    result = await db.execute(
        select(DadoMedico).where(
            DadoMedico.conteudo.ilike(f"%{termo}%") | DadoMedico.titulo.ilike(f"%{termo}%")
        ).limit(50)
    )
    dados = result.scalars().all()
    if not dados:
        raise HTTPException(404, f"Nenhum dado coletado encontrado para '{termo}'. Faça o scraping primeiro.")

    perguntas_template = [
        f"Quais são os sintomas de {termo}?",
        f"Como é feito o diagnóstico de {termo}?",
        f"Qual o tratamento recomendado para {termo}?",
        f"Quais são as complicações de {termo}?",
        f"Como prevenir {termo}?",
    ]

    criados = 0
    for i, dado in enumerate(dados):
        if not dado.conteudo or len(dado.conteudo.strip()) < 50:
            continue
        pergunta = perguntas_template[i % len(perguntas_template)]
        entry = DatasetEntry(
            pergunta=pergunta,
            contexto=f"Fonte: {dado.fonte} - {dado.titulo}",
            resposta=dado.conteudo[:2000],
            categoria=f"scraping_{dado.fonte}",
        )
        db.add(entry)
        criados += 1

    await db.commit()
    await registrar_log(db, "scraping_to_dataset", f"Termo: {termo}, Entradas criadas: {criados}")
    return {"termo": termo, "entradas_criadas": criados}


@router.post("/url-livre")
async def scraping_url_livre(url: str, db: AsyncSession = Depends(get_db)):
    """Faz scraping de uma URL livre, salva como dado médico e gera dataset."""
    import httpx
    from bs4 import BeautifulSoup

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "MedAssist-Academic-Bot/1.0"
            })
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(502, f"Erro ao acessar URL: {type(e).__name__}: {str(e)[:100]}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove scripts e styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    titulo = soup.title.text.strip() if soup.title else url.split("/")[-1]
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup.body
    conteudo = main.get_text(separator="\n", strip=True)[:8000] if main else ""

    if len(conteudo) < 100:
        raise HTTPException(400, "Conteúdo insuficiente na página.")

    # Salva como dado médico
    dado = DadoMedico(
        fonte="url_livre",
        titulo=titulo[:500],
        conteudo=conteudo,
        url=url,
        categoria="scraping_manual",
    )
    db.add(dado)
    await db.commit()
    await db.refresh(dado)

    # Gera dataset automaticamente
    paragrafos = [p.strip() for p in conteudo.split("\n") if len(p.strip()) > 80][:10]
    tema = titulo.split("-")[0].split("|")[0].strip()

    templates = [
        f"O que é {tema}?",
        f"Quais são os sintomas de {tema}?",
        f"Como é o tratamento de {tema}?",
        f"Quais são as causas de {tema}?",
        f"Como prevenir {tema}?",
        f"Qual o diagnóstico de {tema}?",
        f"Quais são as complicações de {tema}?",
        f"Quais exames são indicados para {tema}?",
        f"Qual o prognóstico de {tema}?",
        f"Quais medicamentos são usados para {tema}?",
    ]

    entradas_criadas = 0
    for i, paragrafo in enumerate(paragrafos):
        entry = DatasetEntry(
            pergunta=templates[i % len(templates)],
            contexto=f"Fonte: {titulo} ({url})",
            resposta=paragrafo,
            categoria="url_livre",
        )
        db.add(entry)
        entradas_criadas += 1

    await db.commit()
    await registrar_log(db, "scraping_url_livre", f"URL: {url}, Dataset: {entradas_criadas} entradas")

    return {
        "url": url,
        "titulo": titulo,
        "conteudo_preview": conteudo[:300],
        "dado_medico_id": dado.id,
        "dataset_entradas_criadas": entradas_criadas,
    }


@router.post("/agente-inteligente")
async def agente_inteligente(tema: str, db: AsyncSession = Depends(get_db)):
    """Agente inteligente que usa LLM para planejar, navegar, extrair e gerar dataset automaticamente."""
    from app.services.scraping.agente_llm_scraper import executar_agente_inteligente
    try:
        resultado = await executar_agente_inteligente(db, tema)
    except Exception as e:
        logger.error(f"Agente inteligente falhou: {e}")
        raise HTTPException(502, f"Erro no agente inteligente: {type(e).__name__}: {str(e)[:200]}")
    await registrar_log(db, "agente_inteligente",
        f"Tema: {tema}, Dados: {resultado.total_dados}, Dataset: {resultado.total_dataset}")
    return {
        "tema": resultado.tema,
        "total_dados": resultado.total_dados,
        "total_dataset": resultado.total_dataset,
        "concluido": resultado.concluido,
        "perguntas_planejadas": resultado.perguntas_planejadas,
        "passos": [
            {
                "passo": p.passo,
                "acao": p.acao,
                "fonte": p.fonte,
                "status": p.status,
                "resultado": p.resultado,
                "dados_coletados": p.dados_coletados,
                "dataset_gerado": p.dataset_gerado,
                "itens": [
                    {"titulo": i.titulo, "conteudo_preview": i.conteudo_preview,
                     "url": i.url, "fonte": i.fonte}
                    for i in p.itens
                ],
                "qa_gerados": [
                    {"pergunta": q.pergunta, "resposta_preview": q.resposta_preview,
                     "fonte": q.fonte}
                    for q in p.qa_gerados
                ],
            }
            for p in resultado.passos
        ],
    }
