"""Serviço LangGraph - fluxo de decisão automatizado para triagem e atendimento."""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal


class EstadoTriagem(TypedDict):
    sintomas: str
    sinais_vitais: dict
    classificacao: str
    orientacao: str
    exames_pendentes: list[str]
    alertas: list[str]
    proximo_passo: str


def coletar_sintomas(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: coleta e organiza sintomas."""
    state["alertas"] = []
    state["exames_pendentes"] = []
    return state


def classificar_risco(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: classifica risco Manchester."""
    sinais = state.get("sinais_vitais", {})
    sintomas = state["sintomas"].lower()

    # Regras simplificadas de classificação
    if sinais.get("saturacao", 100) < 90 or "parada" in sintomas:
        state["classificacao"] = "vermelho"
    elif sinais.get("temperatura", 36.5) >= 39.5 or "dor torácica" in sintomas:
        state["classificacao"] = "laranja"
    elif sinais.get("temperatura", 36.5) >= 38.5 or "dor intensa" in sintomas:
        state["classificacao"] = "amarelo"
    elif "dor leve" in sintomas or "resfriado" in sintomas:
        state["classificacao"] = "verde"
    else:
        state["classificacao"] = "verde"
    return state


def verificar_exames(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: verifica exames pendentes baseado nos sintomas."""
    sintomas = state["sintomas"].lower()
    if "dor torácica" in sintomas:
        state["exames_pendentes"].extend(["ECG", "Troponina", "Raio-X Tórax"])
    if "febre" in sintomas:
        state["exames_pendentes"].extend(["Hemograma", "PCR"])
    if "dor abdominal" in sintomas:
        state["exames_pendentes"].extend(["Ultrassom Abdominal", "Hemograma"])
    return state


def gerar_alerta(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: gera alertas para equipe médica."""
    if state["classificacao"] in ("vermelho", "laranja"):
        state["alertas"].append("ALERTA: Paciente requer atendimento IMEDIATO")
        state["alertas"].append(f"Classificação: {state['classificacao'].upper()}")
    if state.get("exames_pendentes"):
        state["alertas"].append(f"Exames solicitados: {', '.join(state['exames_pendentes'])}")
    return state


def definir_orientacao(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: define orientação final."""
    orientacoes = {
        "vermelho": "Encaminhar IMEDIATAMENTE para sala de emergência.",
        "laranja": "Atendimento prioritário. Monitorar sinais vitais.",
        "amarelo": "Aguardar atendimento com monitoramento.",
        "verde": "Aguardar atendimento por ordem de chegada.",
        "azul": "Encaminhar para consulta ambulatorial.",
    }
    state["orientacao"] = orientacoes.get(state["classificacao"], orientacoes["verde"])
    state["proximo_passo"] = "validacao_humana"
    return state


def decidir_urgencia(state: EstadoTriagem) -> Literal["urgente", "normal"]:
    """Decisão condicional de roteamento."""
    if state["classificacao"] in ("vermelho", "laranja"):
        return "urgente"
    return "normal"


def criar_grafo_triagem() -> StateGraph:
    """Cria o grafo de fluxo de triagem."""
    grafo = StateGraph(EstadoTriagem)

    grafo.add_node("coletar", coletar_sintomas)
    grafo.add_node("classificar", classificar_risco)
    grafo.add_node("exames", verificar_exames)
    grafo.add_node("alerta", gerar_alerta)
    grafo.add_node("orientacao", definir_orientacao)

    grafo.set_entry_point("coletar")
    grafo.add_edge("coletar", "classificar")
    grafo.add_conditional_edges("classificar", decidir_urgencia, {
        "urgente": "alerta",
        "normal": "exames",
    })
    grafo.add_edge("exames", "orientacao")
    grafo.add_edge("alerta", "exames")
    grafo.add_edge("orientacao", END)

    return grafo.compile()


# Instância global do grafo
grafo_triagem = criar_grafo_triagem()


async def executar_fluxo_triagem(sintomas: str, sinais_vitais: dict = None) -> dict:
    """Executa o fluxo completo de triagem."""
    estado_inicial = EstadoTriagem(
        sintomas=sintomas,
        sinais_vitais=sinais_vitais or {},
        classificacao="",
        orientacao="",
        exames_pendentes=[],
        alertas=[],
        proximo_passo="",
    )
    resultado = await grafo_triagem.ainvoke(estado_inicial)
    return dict(resultado)
