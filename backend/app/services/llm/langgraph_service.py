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


def _parse_pressao(pa_str: str | None) -> tuple[int, int]:
    """Extrai sistólica e diastólica de uma string como '180/110'. Retorna (0, 0) se inválida."""
    if not pa_str:
        return 0, 0
    try:
        partes = pa_str.strip().split("/")
        return int(partes[0]), int(partes[1])
    except (ValueError, IndexError):
        return 0, 0


def classificar_risco(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: classifica risco Manchester baseado em sintomas + sinais vitais."""
    sinais = state.get("sinais_vitais", {})
    sintomas = state["sintomas"].lower()
    saturacao = sinais.get("saturacao") or 100
    temperatura = sinais.get("temperatura") or 36.5
    fc = sinais.get("frequencia_cardiaca") or 80
    sistolica, diastolica = _parse_pressao(sinais.get("pressao_arterial"))

    # VERMELHO: emergência
    emergencia_sintomas = ["parada", "inconsciente", "sem respiração", "pcr", "hemorragia maciça"]
    if saturacao < 90 or any(s in sintomas for s in emergencia_sintomas):
        state["classificacao"] = "vermelho"
    # LARANJA: muito urgente
    elif (
        saturacao < 95
        or temperatura >= 39.5
        or fc > 130 or fc < 40
        or sistolica > 180 or sistolica < 80
        or diastolica > 120
        or any(s in sintomas for s in [
            "dor torácica", "dor toracica", "dor no peito",
            "convulsão", "convulsao", "avc", "infarto",
            "dificuldade respiratória", "dificuldade respiratoria",
            "delírio", "delirio", "delirante", "confusão mental", "confusao mental",
            "desmaio", "síncope", "sincope", "cianose",
        ])
    ):
        state["classificacao"] = "laranja"
    # AMARELO: urgente
    elif (
        temperatura >= 38.5
        or fc > 120
        or sistolica > 160
        or any(s in sintomas for s in [
            "dor intensa", "febre alta", "vômito", "vomito",
            "fratura", "desidratação", "desidratacao", "sangramento",
        ])
    ):
        state["classificacao"] = "amarelo"
    # VERDE: pouco urgente
    elif any(s in sintomas for s in ["dor leve", "resfriado", "tosse", "dor de cabeça", "mal estar"]):
        state["classificacao"] = "verde"
    # AZUL: não urgente
    elif any(s in sintomas for s in ["receita", "atestado", "rotina", "check-up"]):
        state["classificacao"] = "azul"
    else:
        state["classificacao"] = "verde"
    return state


def verificar_exames(state: EstadoTriagem) -> EstadoTriagem:
    """Nó: verifica exames pendentes baseado nos sintomas e sinais vitais."""
    sintomas = state["sintomas"].lower()
    sinais = state.get("sinais_vitais", {})
    sistolica, _ = _parse_pressao(sinais.get("pressao_arterial"))
    exames = state["exames_pendentes"]

    if any(s in sintomas for s in ["dor torácica", "dor toracica", "dor no peito"]):
        exames.extend(["ECG", "Troponina", "Raio-X Tórax"])
    if any(s in sintomas for s in ["febre", "infecção", "infeccao"]):
        exames.extend(["Hemograma", "PCR", "Hemocultura"])
    if "dor abdominal" in sintomas:
        exames.extend(["Ultrassom Abdominal", "Hemograma"])
    if any(s in sintomas for s in ["confusão", "confusao", "delírio", "delirio", "delirante", "convulsão", "convulsao"]):
        exames.extend(["Tomografia de Crânio", "Glicemia", "Eletrólitos", "Gasometria"])
    if any(s in sintomas for s in ["dispneia", "falta de ar", "dificuldade respirat"]):
        exames.extend(["Gasometria", "Raio-X Tórax", "D-Dímero"])
    if sistolica > 180:
        exames.extend(["ECG", "Função Renal", "Fundo de Olho"])

    # Remove duplicatas mantendo ordem
    seen = set()
    state["exames_pendentes"] = [e for e in exames if not (e in seen or seen.add(e))]
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
    grafo.add_node("orientar", definir_orientacao)

    grafo.set_entry_point("coletar")
    grafo.add_edge("coletar", "classificar")
    grafo.add_conditional_edges("classificar", decidir_urgencia, {
        "urgente": "alerta",
        "normal": "exames",
    })
    grafo.add_edge("exames", "orientar")
    grafo.add_edge("alerta", "exames")
    grafo.add_edge("orientar", END)

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
