"""Service de Chat - gerencia conversas e mensagens."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Conversa, Mensagem


class ChatService:

    @staticmethod
    async def criar_conversa(db: AsyncSession, paciente_id: int | None, tipo: str) -> Conversa:
        conversa = Conversa(paciente_id=paciente_id, tipo=tipo)
        db.add(conversa)
        await db.commit()
        await db.refresh(conversa)
        return conversa

    @staticmethod
    async def adicionar_mensagem(db: AsyncSession, conversa_id: int,
                                  papel: str, conteudo: str, fonte: str = None) -> Mensagem:
        msg = Mensagem(conversa_id=conversa_id, papel=papel, conteudo=conteudo, fonte=fonte)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def obter_conversa(db: AsyncSession, conversa_id: int) -> Conversa | None:
        stmt = (
            select(Conversa)
            .options(selectinload(Conversa.mensagens))
            .where(Conversa.id == conversa_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def historico_mensagens(db: AsyncSession, conversa_id: int) -> list[dict]:
        stmt = (
            select(Mensagem)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.criado_em)
        )
        result = await db.execute(stmt)
        msgs = result.scalars().all()
        return [{"role": m.papel, "content": m.conteudo} for m in msgs]
