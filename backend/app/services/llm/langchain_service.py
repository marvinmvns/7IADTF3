"""Serviço LangChain - integração com LLM (OpenAI/Ollama) + RAG + Web Search + MCP Tools."""
import re
import logging
import httpx
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.config_service import ConfigService
from app.services.rag.rag_service import buscar_contexto, formatar_contexto_para_prompt, formatar_fontes_resposta, buscar_contexto_paciente
from app.services.finetuned_inference import gerar_resposta_finetuned
from app.services.llm.mcp_tools import ALL_TOOLS
from app.config import get_settings

logger = logging.getLogger("medassist.langchain")

SYSTEM_PROMPT_TRIAGEM = """Você é o MedAssist, sistema de apoio à decisão clínica em triagem hospitalar.
{atendimento_context}
Você está conversando com o MÉDICO RESPONSÁVEL, não com o paciente.
Dirija-se SEMPRE ao médico pelo nome (ex: "Dr(a). X, ...").
Ao discutir o caso, referencie o paciente pelo nome em terceira pessoa (ex: "o(a) paciente Y apresenta...").
Sua função: auxiliar na classificação de risco (Protocolo Manchester) e sugerir condutas.
Classificação: Vermelho (emergência), Laranja (muito urgente), Amarelo (urgente), Verde (pouco urgente), Azul (não urgente).
SEMPRE liste diagnósticos diferenciais possíveis com justificativa clínica.
Sugira exames complementares e condutas para validação do médico.
NUNCA prescreva diretamente. Cite fontes e protocolos.

{rag_context}"""

SYSTEM_PROMPT_CONSULTA = """Você é o MedAssist, sistema de apoio à decisão clínica hospitalar.
{atendimento_context}
Você está conversando com o MÉDICO RESPONSÁVEL, não com o paciente.
Dirija-se SEMPRE ao médico pelo nome (ex: "Dr(a). X, com base no histórico de Y...").
Referencie o paciente em terceira pessoa ao discutir seu quadro clínico.
Auxilie com: condutas clínicas, diagnósticos diferenciais, protocolos, interações medicamentosas.
Considere o histórico completo do paciente (alergias, medicamentos em uso, diagnósticos prévios).
Sugira exames complementares quando pertinente.
Cite fontes e protocolos utilizados.
NUNCA prescreva — apenas sugira condutas para validação do médico.

{rag_context}"""

SYSTEM_PROMPT_GERAL = """Você é o MedAssist, sistema de apoio à decisão clínica hospitalar.
{atendimento_context}
Você está conversando com o MÉDICO RESPONSÁVEL, não com o paciente.
Dirija-se ao médico pelo nome. Referencie o paciente em terceira pessoa.
Auxilie com informações de saúde, protocolos e orientações clínicas.
Cite fontes quando possível.

{rag_context}"""

PROMPTS = {
    "triagem": SYSTEM_PROMPT_TRIAGEM,
    "consulta": SYSTEM_PROMPT_CONSULTA,
    "geral": SYSTEM_PROMPT_GERAL,
}

WEB_CONTEXT_HEADER = """
--- CONTEXTO WEB (Brave Search) ---
Informações recentes encontradas na web. Use como referência complementar e cite as fontes.

{web_resultados}
--- FIM DO CONTEXTO WEB ---"""

MEDICAL_KEYWORDS = [
    "sintoma", "sintomas", "doença", "doenças", "tratamento", "tratamentos",
    "medicamento", "medicamentos", "diagnóstico", "diagnósticos", "saúde",
    "médico", "médica", "hospital", "clínica", "cirurgia", "exame", "exames",
    "dor", "febre", "infecção", "vírus", "bactéria", "alergia", "remédio",
    "terapia", "vacina", "prevenção", "patologia", "enfermidade", "cura",
    "prescrição", "receita", "dose", "posologia", "efeito colateral",
]

# Palavras-chave que indicam necessidade de buscar dados do paciente
PATIENT_KEYWORDS = [
    "paciente", "cpf", "ficha", "prontuário", "prontuario", "triagem",
    "triagens", "cadastro", "dados", "histórico", "historico", "atendimento",
    "listar", "lista", "quem", "alergias", "medicamentos", "consultas",
]

RAG_CONTEXT_HEADER = """
--- CONTEXTO RECUPERADO (Base de Conhecimento) ---
Use as informações abaixo para fundamentar sua resposta. Cite as fontes quando utilizá-las.
Se o contexto não for relevante para a pergunta, ignore-o e responda com seu conhecimento geral.

{contexto}
--- FIM DO CONTEXTO ---"""


class LangChainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def _get_llm(self):
        config = await ConfigService.obter_ativa(self.db)
        provider = config.provider if config else self.settings.llm_provider

        if provider == "ollama":
            return ChatOllama(
                base_url=config.base_url or self.settings.ollama_url,
                model=config.model_name or self.settings.ollama_model,
                temperature=config.temperature if config else 0.7,
            )

        if provider == "finetuned":
            # Modelo fine-tuned local via transformers + PEFT
            from app.services.finetuned_inference import _load_finetuned_as_llm
            return await _load_finetuned_as_llm(
                self.db,
                model_name=config.model_name if config else None,
                temperature=config.temperature if config else 0.7,
                max_tokens=config.max_tokens if config else 2048,
            )

        if provider == "llama-cpp":
            # llama-server expõe API compatível com OpenAI
            base_url = (config.base_url if config else None) or self.settings.llama_cpp_url
            model_name = config.model_name if config else "qwen3.5"
            # reasoning_effort só para modelos Qwen 3.5 (têm modo thinking)
            model_kwargs = {}
            if "qwen3.5" in model_name.lower() or "qwen3_5" in model_name.lower():
                model_kwargs["reasoning_effort"] = "none"
            return ChatOpenAI(
                api_key="not-needed",
                base_url=f"{base_url}/v1",
                model=model_name,
                temperature=config.temperature if config else 0.7,
                max_tokens=config.max_tokens if config else 2048,
                model_kwargs=model_kwargs if model_kwargs else {},
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

    def _is_medical_query(self, pergunta: str) -> bool:
        """Verifica se a pergunta contém termos médicos/de saúde."""
        pergunta_lower = pergunta.lower()
        return any(keyword in pergunta_lower for keyword in MEDICAL_KEYWORDS)

    def _needs_patient_tools(self, pergunta: str) -> bool:
        """Verifica se a pergunta precisa de ferramentas de busca de pacientes."""
        pergunta_lower = pergunta.lower()
        return any(keyword in pergunta_lower for keyword in PATIENT_KEYWORDS)

    def _buscar_web(self, pergunta: str) -> str:
        """Busca na web via Brave Search API para perguntas médicas."""
        try:
            api_key = self.settings.brave_search_api_key
            if not api_key:
                return ""

            if not self._is_medical_query(pergunta):
                return ""

            response = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": pergunta, "count": 3, "search_lang": "pt-br"},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("web", {}).get("results", [])
            if not results:
                return ""

            formatted_parts = []
            for r in results[:3]:
                title = r.get("title", "")
                description = r.get("description", "")
                url = r.get("url", "")
                formatted_parts.append(f"- {title}: {description} (Fonte: {url})")

            web_text = "\n".join(formatted_parts)
            logger.info(f"Web Search: {len(results[:3])} resultados para '{pergunta[:50]}...'")
            return WEB_CONTEXT_HEADER.format(web_resultados=web_text)
        except Exception as e:
            logger.warning(f"Brave Search indisponível: {e}")
            return ""

    def _buscar_rag(self, pergunta: str, tipo: str) -> tuple[str, list[dict]]:
        """Busca contexto RAG relevante para a pergunta."""
        try:
            contextos = buscar_contexto(pergunta, n_resultados=5)
            if not contextos:
                return "", []

            texto_contexto = formatar_contexto_para_prompt(contextos)
            rag_block = RAG_CONTEXT_HEADER.format(contexto=texto_contexto)
            logger.info(f"RAG: {len(contextos)} documentos recuperados para '{pergunta[:50]}...'")
            return rag_block, contextos
        except Exception as e:
            logger.warning(f"RAG indisponível: {e}")
            return "", []

    def _montar_atendimento_context(self, medico_nome: str = None, medico_crm: str = None,
                                      paciente_nome: str = None) -> str:
        """Monta o bloco de contexto do atendimento (médico + paciente)."""
        partes = []
        if medico_nome:
            crm_str = f" (CRM: {medico_crm})" if medico_crm else ""
            partes.append(f"Médico responsável: {medico_nome}{crm_str}")
        if paciente_nome:
            partes.append(f"Paciente em atendimento: {paciente_nome}")
        if partes:
            return "\n".join(partes)
        return ""

    async def _get_paciente_nome(self, db: AsyncSession, paciente_id: int) -> str:
        """Busca o nome do paciente pelo ID."""
        try:
            from sqlalchemy import select
            from app.models.models import Paciente
            result = await db.execute(select(Paciente.nome).where(Paciente.id == paciente_id))
            nome = result.scalar_one_or_none()
            return nome or ""
        except Exception:
            return ""

    async def responder(self, pergunta: str, historico: list[dict], tipo: str = "geral",
                        paciente_id: int = None, db: AsyncSession = None,
                        medico_nome: str = None, medico_crm: str = None):
        llm = await self._get_llm()

        # RAG: busca contexto relevante
        rag_context, contextos_usados = self._buscar_rag(pergunta, tipo)

        # Web Search: busca complementar via Brave Search
        web_context = self._buscar_web(pergunta)

        # Fine-tuned: consulta modelo especializado
        finetuned_context = ""
        if db and self._is_medical_query(pergunta):
            try:
                ft_resp = await gerar_resposta_finetuned(db, pergunta, max_tokens=256)
                if ft_resp:
                    finetuned_context = (
                        f"\n--- RESPOSTA DO MODELO ESPECIALIZADO (Fine-Tuned) ---\n"
                        f"{ft_resp}\n"
                        f"--- FIM MODELO ESPECIALIZADO ---"
                    )
                    logger.info(f"Fine-tuned contribuiu com {len(ft_resp)} chars")
            except Exception as e:
                logger.warning(f"Fine-tuned indisponível: {e}")

        # Contexto do paciente: busca dados diretos do banco
        paciente_context = ""
        if paciente_id and db:
            try:
                paciente_context = await buscar_contexto_paciente(db, paciente_id)
            except Exception as e:
                logger.warning(f"Falha ao buscar contexto do paciente {paciente_id}: {e}")

        # Monta contexto completo (RAG + Fine-tuned + Web + paciente)
        contexto_completo = rag_context
        if finetuned_context:
            contexto_completo = f"{contexto_completo}\n\n{finetuned_context}" if contexto_completo else finetuned_context
        if web_context:
            contexto_completo = f"{contexto_completo}\n\n{web_context}" if contexto_completo else web_context
        if paciente_context:
            contexto_completo = f"{paciente_context}\n\n{contexto_completo}" if contexto_completo else paciente_context

        # Monta contexto do atendimento (médico + paciente)
        paciente_nome = ""
        if paciente_id and db:
            paciente_nome = await self._get_paciente_nome(db, paciente_id)
        atendimento_ctx = self._montar_atendimento_context(medico_nome, medico_crm, paciente_nome)

        system_prompt = PROMPTS.get(tipo, PROMPTS["geral"])
        system_prompt_final = system_prompt.format(
            rag_context=contexto_completo,
            atendimento_context=atendimento_ctx,
        )

        msgs = []
        for m in historico[:-1]:
            if m["role"] == "user":
                msgs.append(HumanMessage(content=m["content"]))
            else:
                msgs.append(AIMessage(content=m["content"]))

        use_tools = self._needs_patient_tools(pergunta)

        if use_tools:
            try:
                return await self._responder_com_tools(
                    llm, pergunta, msgs, system_prompt_final,
                    contextos_usados, web_context
                )
            except Exception as e:
                logger.warning(f"Agent com tools falhou, usando chain simples: {e}")
                # Fallback para chain simples

        # Chain simples (sem tools)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_final),
            MessagesPlaceholder("historico"),
            ("human", "{pergunta}"),
        ])
        chain = prompt | llm
        resp = await chain.ainvoke({"pergunta": pergunta, "historico": msgs})

        # Monta fonte
        provider_info = await self._get_provider_info()
        fonte_parts = [f"LLM: {provider_info}"]
        if contextos_usados:
            rag_fontes = formatar_fontes_resposta(contextos_usados)
            if rag_fontes:
                fonte_parts.append(f"RAG: {rag_fontes}")
        if finetuned_context:
            fonte_parts.append("Fine-Tuned: Modelo Especializado")
        if web_context:
            fonte_parts.append("Web: Brave Search")

        fonte = " | ".join(fonte_parts)
        # Remove blocos <think>...</think> de modelos thinking
        content = re.sub(r'<think>.*?</think>', '', resp.content, flags=re.DOTALL).strip()
        return content, fonte

    async def preparar_contexto(self, pergunta: str, historico: list[dict], tipo: str = "geral",
                                 paciente_id: int = None, db: AsyncSession = None,
                                 medico_nome: str = None, medico_crm: str = None) -> tuple[str, str]:
        """Prepara todo o contexto e monta o system prompt final. Retorna (prompt_final, fontes)."""
        rag_context, contextos_usados = self._buscar_rag(pergunta, tipo)
        web_context = self._buscar_web(pergunta)

        finetuned_context = ""
        if db and self._is_medical_query(pergunta):
            try:
                ft_resp = await gerar_resposta_finetuned(db, pergunta, max_tokens=256)
                if ft_resp:
                    finetuned_context = (
                        f"\n--- RESPOSTA DO MODELO ESPECIALIZADO (Fine-Tuned) ---\n"
                        f"{ft_resp}\n--- FIM MODELO ESPECIALIZADO ---"
                    )
            except Exception:
                pass

        paciente_context = ""
        if paciente_id and db:
            try:
                paciente_context = await buscar_contexto_paciente(db, paciente_id)
            except Exception:
                pass

        contexto = rag_context
        if finetuned_context:
            contexto = f"{contexto}\n\n{finetuned_context}" if contexto else finetuned_context
        if web_context:
            contexto = f"{contexto}\n\n{web_context}" if contexto else web_context
        if paciente_context:
            contexto = f"{paciente_context}\n\n{contexto}" if contexto else paciente_context

        # Monta contexto do atendimento
        paciente_nome = ""
        if paciente_id and db:
            paciente_nome = await self._get_paciente_nome(db, paciente_id)
        atendimento_ctx = self._montar_atendimento_context(medico_nome, medico_crm, paciente_nome)

        system_prompt = PROMPTS.get(tipo, PROMPTS["geral"])
        prompt_final = system_prompt.format(
            rag_context=contexto,
            atendimento_context=atendimento_ctx,
        )

        # Monta fontes
        provider_info = await self._get_provider_info()
        fonte_parts = [f"LLM: {provider_info}"]
        if contextos_usados:
            rag_fontes = formatar_fontes_resposta(contextos_usados)
            if rag_fontes:
                fonte_parts.append(f"RAG: {rag_fontes}")
        if finetuned_context:
            fonte_parts.append("Fine-Tuned: Modelo Especializado")
        if web_context:
            fonte_parts.append("Web: Brave Search")

        return prompt_final, " | ".join(fonte_parts)

    async def stream_resposta(self, pergunta: str, historico: list[dict],
                               tipo: str, system_prompt_final: str):
        """Gera resposta em streaming (token por token).
        Filtra blocos <think>...</think> de modelos thinking (ex: Qwen 3.5),
        emitindo apenas um marcador de thinking sem exibir o conteúdo.
        """
        llm = await self._get_llm()

        msgs = []
        for m in historico[:-1]:
            if m["role"] == "user":
                msgs.append(HumanMessage(content=m["content"]))
            else:
                msgs.append(AIMessage(content=m["content"]))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_final),
            MessagesPlaceholder("historico"),
            ("human", "{pergunta}"),
        ])
        chain = prompt | llm

        inside_think = False
        think_buffer = ""

        async for chunk in chain.astream({"pergunta": pergunta, "historico": msgs}):
            if not hasattr(chunk, 'content') or not chunk.content:
                continue

            text = chunk.content

            # Se estamos dentro de um bloco <think>, acumular até encontrar </think>
            if inside_think:
                think_buffer += text
                if "</think>" in think_buffer:
                    # Fim do bloco thinking - extrair texto após </think>
                    after = think_buffer.split("</think>", 1)[1]
                    inside_think = False
                    think_buffer = ""
                    if after.strip():
                        yield after
                continue

            # Verificar se o chunk inicia um bloco <think>
            if "<think>" in text:
                before, after = text.split("<think>", 1)
                if before.strip():
                    yield before
                # Sinaliza thinking (marcador especial)
                yield "\u200B"  # zero-width space como marcador
                inside_think = True
                think_buffer = after
                # Verificar se </think> já está no mesmo chunk
                if "</think>" in think_buffer:
                    after_close = think_buffer.split("</think>", 1)[1]
                    inside_think = False
                    think_buffer = ""
                    if after_close.strip():
                        yield after_close
                continue

            yield text

    async def _responder_com_tools(self, llm, pergunta: str, historico: list,
                                    system_prompt: str, contextos_usados: list,
                                    web_context: str):
        """Usa LangGraph ReAct Agent com MCP tools para buscar dados de pacientes."""
        logger.info(f"Usando agent com MCP tools para: '{pergunta[:60]}...'")

        # Cria agent ReAct com as ferramentas MCP
        agent = create_react_agent(llm, ALL_TOOLS, prompt=system_prompt)

        # Monta mensagens: histórico + pergunta atual
        messages = list(historico) + [HumanMessage(content=pergunta)]

        result = await agent.ainvoke({"messages": messages})

        # Extrai resposta do último AIMessage
        resposta = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                resposta = msg.content
                break

        if not resposta:
            resposta = result["messages"][-1].content if result["messages"] else "Não foi possível processar."

        # Monta fonte
        provider_info = f"LLM+MCP: {await self._get_provider_info()}"
        fonte_parts = [provider_info, "MCP Tools: dados do paciente"]
        if contextos_usados:
            rag_fontes = formatar_fontes_resposta(contextos_usados)
            if rag_fontes:
                fonte_parts.append(f"RAG: {rag_fontes}")
        if web_context:
            fonte_parts.append("Web: Brave Search")

        fonte = " | ".join(fonte_parts)
        return resposta, fonte

    async def orientar_triagem(self, sintomas: str) -> str:
        llm = await self._get_llm()

        # RAG para triagem
        rag_context, _ = self._buscar_rag(sintomas, "triagem")
        system_prompt = SYSTEM_PROMPT_TRIAGEM.format(rag_context=rag_context)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
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
