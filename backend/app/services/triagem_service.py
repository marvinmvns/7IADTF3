"""Service de Triagem com classificação de risco Manchester simplificada."""
import json
import re
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Triagem
from app.schemas.schemas import TriagemCreate
from app.services.llm.langgraph_service import executar_fluxo_triagem
from app.services.llm.langchain_service import LangChainService

logger = logging.getLogger("medassist")


PALAVRAS_RISCO = {
    "vermelho": ["parada cardíaca", "sem respiração", "inconsciente", "hemorragia grave", "choque"],
    "laranja": ["dor torácica", "dificuldade respiratória", "convulsão", "avc", "infarto"],
    "amarelo": ["febre alta", "dor intensa", "vômito persistente", "fratura", "desidratação"],
    "verde": ["dor leve", "resfriado", "tosse", "dor de cabeça", "mal estar"],
    "azul": ["receita", "atestado", "consulta rotina", "exame de rotina", "check-up"],
}

# Ordem de urgência: menor índice = mais urgente
ORDEM_URGENCIA = ["vermelho", "laranja", "amarelo", "verde", "azul"]

PROMPT_CLASSIFICACAO_LLM = """Você é um médico emergencista experiente realizando triagem hospitalar.
Analise os seguintes dados do paciente e forneça uma avaliação clínica.

Sintomas: {sintomas}
Sinais Vitais:
- Pressão Arterial: {pa}
- Temperatura: {temp}°C
- Frequência Cardíaca: {fc} bpm
- Saturação O2: {spo2}%

Responda APENAS em formato JSON válido, sem markdown, sem texto adicional:
{{
  "classificacao_manchester": "vermelho|laranja|amarelo|verde|azul",
  "nivel_urgencia": 1,
  "diagnosticos_possiveis": ["diagnóstico 1", "diagnóstico 2"],
  "conduta_sugerida": "texto",
  "justificativa": "texto"
}}

Regras:
- classificacao_manchester deve ser exatamente uma das cores: vermelho, laranja, amarelo, verde, azul
- nivel_urgencia deve ser um número inteiro de 1 (menos urgente) a 10 (mais urgente)
- diagnosticos_possiveis deve conter pelo menos 1 diagnóstico possível
- Considere os sinais vitais em conjunto com os sintomas para a classificação
- Pressão arterial sistólica > 180 ou < 90 indica urgência elevada
- Temperatura > 39.5°C indica urgência elevada
- Frequência cardíaca > 120 ou < 50 indica urgência elevada
- Saturação < 90% indica emergência, < 95% indica urgência"""


class TriagemService:

    @staticmethod
    def classificar_risco(sintomas: str, temperatura: float | None = None,
                          saturacao: int | None = None) -> str:
        texto = sintomas.lower()

        # Sinais vitais críticos
        if temperatura and temperatura >= 39.5:
            return "laranja"
        if saturacao and saturacao < 90:
            return "vermelho"
        if saturacao and saturacao < 95:
            return "laranja"

        # Classificação por palavras-chave
        for cor, palavras in PALAVRAS_RISCO.items():
            if any(p in texto for p in palavras):
                return cor

        return "verde"

    @staticmethod
    async def classificar_com_llm(db: AsyncSession, sintomas: str, sinais_vitais: dict) -> dict | None:
        """Classifica usando LLM com análise de sintomas e sinais vitais.

        Returns dict with keys: classificacao_manchester, nivel_urgencia,
        diagnosticos_possiveis, conduta_sugerida, justificativa.
        Returns None if LLM call fails.
        """
        try:
            service = LangChainService(db)
            llm = await service._get_llm()

            pa = sinais_vitais.get("pressao_arterial") or "não informada"
            temp = sinais_vitais.get("temperatura") or "não informada"
            fc = sinais_vitais.get("frequencia_cardiaca") or "não informada"
            spo2 = sinais_vitais.get("saturacao") or "não informada"

            prompt_text = PROMPT_CLASSIFICACAO_LLM.format(
                sintomas=sintomas, pa=pa, temp=temp, fc=fc, spo2=spo2
            )

            resp = await llm.ainvoke(prompt_text)
            conteudo = resp.content.strip()

            # Remove blocos <think>...</think> de modelos thinking
            conteudo = re.sub(r'<think>.*?</think>', '', conteudo, flags=re.DOTALL).strip()

            # Try to extract JSON from potential markdown code blocks
            if "```" in conteudo:
                start = conteudo.find("{")
                end = conteudo.rfind("}") + 1
                if start != -1 and end > start:
                    conteudo = conteudo[start:end]

            resultado = json.loads(conteudo)

            # Validate required fields
            classificacao = resultado.get("classificacao_manchester", "").lower()
            if classificacao not in ("vermelho", "laranja", "amarelo", "verde", "azul"):
                logger.warning(f"LLM retornou classificação inválida: {classificacao}")
                return None

            nivel = resultado.get("nivel_urgencia")
            if not isinstance(nivel, int) or nivel < 1 or nivel > 10:
                logger.warning(f"LLM retornou nível de urgência inválido: {nivel}")
                return None

            diagnosticos = resultado.get("diagnosticos_possiveis", [])
            if not isinstance(diagnosticos, list) or len(diagnosticos) == 0:
                logger.warning("LLM retornou diagnósticos inválidos")
                return None

            return {
                "classificacao_manchester": classificacao,
                "nivel_urgencia": nivel,
                "diagnosticos_possiveis": diagnosticos,
                "conduta_sugerida": resultado.get("conduta_sugerida", ""),
                "justificativa": resultado.get("justificativa", ""),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"LLM retornou JSON inválido: {e}")
            return None
        except Exception as e:
            logger.warning(f"Classificação LLM falhou: {e}")
            return None

    @staticmethod
    async def executar_langgraph(sintomas: str, sinais_vitais: dict) -> dict | None:
        """Executa fluxo LangGraph, retorna None em caso de falha."""
        try:
            resultado = await executar_fluxo_triagem(sintomas, sinais_vitais)
            return resultado
        except Exception as e:
            logger.warning(f"LangGraph falhou, usando fallback: {e}")
            return None

    @staticmethod
    async def criar(db: AsyncSession, dados: TriagemCreate, orientacao_ia: str = "") -> Triagem:
        sinais_vitais = {
            "temperatura": dados.temperatura,
            "saturacao": dados.saturacao,
            "frequencia_cardiaca": dados.frequencia_cardiaca,
            "pressao_arterial": dados.pressao_arterial,
        }

        # Step 1: LLM classification for nivel_urgencia and diagnosticos
        resultado_llm = await TriagemService.classificar_com_llm(
            db, dados.sintomas, sinais_vitais
        )

        nivel_urgencia = None
        diagnosticos_possiveis = None
        classificacao_llm = None

        if resultado_llm:
            nivel_urgencia = resultado_llm["nivel_urgencia"]
            diagnosticos_possiveis = json.dumps(
                resultado_llm["diagnosticos_possiveis"], ensure_ascii=False
            )
            classificacao_llm = resultado_llm["classificacao_manchester"]
            # Build orientation from LLM result
            llm_orientacao_parts = []
            if resultado_llm.get("conduta_sugerida"):
                llm_orientacao_parts.append(f"Conduta sugerida: {resultado_llm['conduta_sugerida']}")
            if resultado_llm.get("justificativa"):
                llm_orientacao_parts.append(f"Justificativa: {resultado_llm['justificativa']}")
            if llm_orientacao_parts:
                orientacao_ia = " | ".join(llm_orientacao_parts)

        # Step 2: LangGraph flow for exames/alertas
        resultado_lg = await TriagemService.executar_langgraph(
            dados.sintomas, sinais_vitais
        )

        if resultado_lg:
            classificacao_lg = resultado_lg.get("classificacao", "")
            orientacao_lg = resultado_lg.get("orientacao", "")
            exames_pendentes = resultado_lg.get("exames_pendentes", [])
            alertas = resultado_lg.get("alertas", [])

            # Usa a classificação MAIS URGENTE entre LLM e LangGraph
            if classificacao_llm and classificacao_lg:
                idx_llm = ORDEM_URGENCIA.index(classificacao_llm) if classificacao_llm in ORDEM_URGENCIA else 99
                idx_lg = ORDEM_URGENCIA.index(classificacao_lg) if classificacao_lg in ORDEM_URGENCIA else 99
                classificacao = classificacao_llm if idx_llm <= idx_lg else classificacao_lg
            else:
                classificacao = classificacao_llm or classificacao_lg or "verde"
        else:
            # Fallback: use LLM classification or keyword-based
            classificacao = classificacao_llm or TriagemService.classificar_risco(
                dados.sintomas, dados.temperatura, dados.saturacao
            )
            orientacao_lg = ""
            exames_pendentes = []
            alertas = []

        # Enrich orientation with LangGraph exams and alerts
        partes_orientacao = [orientacao_ia] if orientacao_ia else []
        if orientacao_lg and orientacao_lg != orientacao_ia:
            partes_orientacao.append(orientacao_lg)
        if exames_pendentes:
            partes_orientacao.append(f"Exames sugeridos: {', '.join(exames_pendentes)}")
        if alertas:
            partes_orientacao.append(f"Alertas: {'; '.join(alertas)}")
        orientacao_final = " | ".join(partes_orientacao) if partes_orientacao else ""

        triagem = Triagem(
            **dados.model_dump(),
            classificacao_risco=classificacao,
            orientacao_ia=orientacao_final,
            nivel_urgencia=nivel_urgencia,
            diagnosticos_possiveis=diagnosticos_possiveis,
        )
        db.add(triagem)
        await db.commit()
        await db.refresh(triagem)
        return triagem

    @staticmethod
    async def listar_por_paciente(db: AsyncSession, paciente_id: int):
        stmt = select(Triagem).where(Triagem.paciente_id == paciente_id)
        result = await db.execute(stmt)
        return result.scalars().all()
