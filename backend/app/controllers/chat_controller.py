"""Controller de Chat - interface conversacional com IA."""
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import MensagemIn, MensagemOut, ConversaOut
from app.services.chat_service import ChatService
from app.services.llm.langchain_service import LangChainService
from app.services.tts.tts_service import TTSService
from app.services.tts.stt_service import STTService
from app.utils.logger import registrar_log
import io

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/mensagem", response_model=MensagemOut)
async def enviar_mensagem(msg: MensagemIn, db: AsyncSession = Depends(get_db)):
    # Cria conversa se não existir
    if not msg.conversa_id:
        conversa = await ChatService.criar_conversa(db, msg.paciente_id, msg.tipo)
        msg.conversa_id = conversa.id

    # Salva mensagem do usuário
    await ChatService.adicionar_mensagem(db, msg.conversa_id, "user", msg.conteudo)

    # Obtém histórico e gera resposta
    historico = await ChatService.historico_mensagens(db, msg.conversa_id)
    llm = LangChainService(db)
    resposta, fonte = await llm.responder(msg.conteudo, historico, msg.tipo)

    # Salva resposta do assistente
    msg_resp = await ChatService.adicionar_mensagem(
        db, msg.conversa_id, "assistant", resposta, fonte
    )
    await registrar_log(db, "chat_resposta", f"Conversa #{msg.conversa_id}", "ia")
    return msg_resp


@router.get("/conversa/{conversa_id}", response_model=ConversaOut)
async def obter_conversa(conversa_id: int, db: AsyncSession = Depends(get_db)):
    conversa = await ChatService.obter_conversa(db, conversa_id)
    if not conversa:
        from fastapi import HTTPException
        raise HTTPException(404, "Conversa não encontrada")
    return conversa


@router.post("/voz-para-texto")
async def voz_para_texto(audio: UploadFile = File(...)):
    conteudo = await audio.read()
    texto = await STTService.transcrever(conteudo)
    return {"texto": texto}


@router.post("/texto-para-voz")
async def texto_para_voz(texto: str):
    audio_bytes = await TTSService.sintetizar(texto)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")
