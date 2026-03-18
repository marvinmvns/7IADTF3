"""Controller de Chat - interface conversacional com IA."""
import json
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, SessionLocal
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
    paciente_id = msg.paciente_id
    if not msg.conversa_id:
        conversa = await ChatService.criar_conversa(db, paciente_id, msg.tipo)
        msg.conversa_id = conversa.id
    elif paciente_id is None:
        conversa = await ChatService.obter_conversa(db, msg.conversa_id)
        if conversa and conversa.paciente_id:
            paciente_id = conversa.paciente_id

    await ChatService.adicionar_mensagem(db, msg.conversa_id, "user", msg.conteudo)
    await registrar_log(db, "chat_mensagem_usuario",
        f"Conversa #{msg.conversa_id} - Paciente: {paciente_id} - Medico: {msg.medico_nome or 'N/A'}")

    historico = await ChatService.historico_mensagens(db, msg.conversa_id)
    llm = LangChainService(db)
    resposta, fonte = await llm.responder(
        msg.conteudo, historico, msg.tipo,
        paciente_id=paciente_id, db=db,
        medico_nome=msg.medico_nome, medico_crm=msg.medico_crm,
    )

    msg_resp = await ChatService.adicionar_mensagem(
        db, msg.conversa_id, "assistant", resposta, fonte
    )
    await registrar_log(db, "chat_resposta", f"Conversa #{msg.conversa_id}", "ia")
    return msg_resp


@router.post("/mensagem-stream")
async def enviar_mensagem_stream(msg: MensagemIn, db: AsyncSession = Depends(get_db)):
    """Envia mensagem e retorna resposta via Server-Sent Events (streaming)."""
    paciente_id = msg.paciente_id
    if not msg.conversa_id:
        conversa = await ChatService.criar_conversa(db, paciente_id, msg.tipo)
        msg.conversa_id = conversa.id
    elif paciente_id is None:
        conversa = await ChatService.obter_conversa(db, msg.conversa_id)
        if conversa and conversa.paciente_id:
            paciente_id = conversa.paciente_id

    await ChatService.adicionar_mensagem(db, msg.conversa_id, "user", msg.conteudo)
    await registrar_log(db, "chat_mensagem_usuario",
        f"Conversa #{msg.conversa_id} - Paciente: {paciente_id} - Medico: {msg.medico_nome or 'N/A'}")

    historico = await ChatService.historico_mensagens(db, msg.conversa_id)
    llm_service = LangChainService(db)

    contexto_completo, fontes = await llm_service.preparar_contexto(
        msg.conteudo, historico, msg.tipo,
        paciente_id=paciente_id, db=db,
        medico_nome=msg.medico_nome, medico_crm=msg.medico_crm,
    )

    conversa_id = msg.conversa_id

    async def gerar_stream():
        resposta_completa = ""
        thinking_notified = False
        try:
            async for chunk in llm_service.stream_resposta(
                msg.conteudo, historico, msg.tipo, contexto_completo
            ):
                # Marcador de thinking (zero-width space) - notifica o frontend
                if chunk == "\u200B":
                    if not thinking_notified:
                        yield f"data: {json.dumps({'thinking': True})}\n\n"
                        thinking_notified = True
                    continue
                resposta_completa += chunk
                yield f"data: {json.dumps({'token': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True, 'fonte': fontes, 'conversa_id': conversa_id})}\n\n"

            async with SessionLocal() as save_db:
                await ChatService.adicionar_mensagem(
                    save_db, conversa_id, "assistant", resposta_completa, fontes
                )
                await registrar_log(save_db, "chat_resposta", f"Conversa #{conversa_id}", "ia")

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(gerar_stream(), media_type="text/event-stream")


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
