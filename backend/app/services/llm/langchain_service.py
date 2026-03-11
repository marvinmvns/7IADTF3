"""Serviço LangChain - integração com LLM (OpenAI/Ollama)."""
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.config_service import ConfigService
from app.config import get_settings

SYSTEM_PROMPT_TRIAGEM = """Você é um assistente de triagem médica hospitalar.
Sua função é coletar sintomas, classificar o risco (Manchester) e orientar o paciente.
Classificação: Vermelho (emergência), Laranja (muito urgente), Amarelo (urgente), Verde (pouco urgente), Azul (não urgente).
NUNCA prescreva medicamentos diretamente. Sempre indique que a validação humana é necessária.
Indique a fonte da informação quando possível."""

SYSTEM_PROMPT_CONSULTA = """Você é um assistente médico virtual de um hospital.
Auxilie com informações sobre condutas clínicas, protocolos e procedimentos.
Baseie-se em protocolos médicos reconhecidos. Sempre cite a fonte.
NUNCA prescreva sem validação humana. Indique quando o médico deve ser consultado."""

SYSTEM_PROMPT_GERAL = """Você é o MedAssist, assistente virtual de um hospital.
Ajude com informações gerais de saúde, agendamentos e dúvidas.
Seja empático e claro. Indique fontes quando possível.
Para questões médicas específicas, oriente a buscar atendimento presencial."""

PROMPTS = {
    "triagem": SYSTEM_PROMPT_TRIAGEM,
    "consulta": SYSTEM_PROMPT_CONSULTA,
    "geral": SYSTEM_PROMPT_GERAL,
}


class LangChainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def _get_llm(self):
        config = await ConfigService.obter_ativa(self.db)
        if config and config.provider == "ollama":
            return ChatOllama(
                base_url=config.base_url or self.settings.ollama_url,
                model=config.model_name or self.settings.ollama_model,
                temperature=config.temperature,
            )
        # Padrão: OpenAI
        api_key = (config.api_key if config else None) or self.settings.openai_api_key
        model = (config.model_name if config else None) or self.settings.openai_model
        return ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=config.temperature if config else 0.7,
            max_tokens=config.max_tokens if config else 2048,
        )

    async def responder(self, pergunta: str, historico: list[dict], tipo: str = "geral"):
        llm = await self._get_llm()
        system_prompt = PROMPTS.get(tipo, PROMPTS["geral"])

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("historico"),
            ("human", "{pergunta}"),
        ])

        msgs = []
        for m in historico[:-1]:  # exclui a última (é a pergunta atual)
            if m["role"] == "user":
                msgs.append(HumanMessage(content=m["content"]))
            else:
                msgs.append(AIMessage(content=m["content"]))

        chain = prompt | llm
        resp = await chain.ainvoke({"pergunta": pergunta, "historico": msgs})

        fonte = "LLM: " + (await self._get_provider_info())
        return resp.content, fonte

    async def orientar_triagem(self, sintomas: str) -> str:
        llm = await self._get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_TRIAGEM),
            ("human", "Paciente relata: {sintomas}\n\nClassifique o risco e oriente."),
        ])
        chain = prompt | llm
        resp = await chain.ainvoke({"sintomas": sintomas})
        return resp.content

    async def _get_provider_info(self) -> str:
        config = await ConfigService.obter_ativa(self.db)
        if config:
            return f"{config.provider}/{config.model_name}"
        return f"{self.settings.llm_provider}/{self.settings.openai_model}"
