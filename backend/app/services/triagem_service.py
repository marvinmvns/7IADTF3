"""Service de Triagem com classificação de risco Manchester simplificada."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Triagem
from app.schemas.schemas import TriagemCreate


PALAVRAS_RISCO = {
    "vermelho": ["parada cardíaca", "sem respiração", "inconsciente", "hemorragia grave", "choque"],
    "laranja": ["dor torácica", "dificuldade respiratória", "convulsão", "avc", "infarto"],
    "amarelo": ["febre alta", "dor intensa", "vômito persistente", "fratura", "desidratação"],
    "verde": ["dor leve", "resfriado", "tosse", "dor de cabeça", "mal estar"],
    "azul": ["receita", "atestado", "consulta rotina", "exame de rotina", "check-up"],
}


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
    async def criar(db: AsyncSession, dados: TriagemCreate, orientacao_ia: str = "") -> Triagem:
        classificacao = TriagemService.classificar_risco(
            dados.sintomas, dados.temperatura, dados.saturacao
        )
        triagem = Triagem(
            **dados.model_dump(),
            classificacao_risco=classificacao,
            orientacao_ia=orientacao_ia,
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
