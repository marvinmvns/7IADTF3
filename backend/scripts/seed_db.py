"""Seed do banco de dados com dados de exemplo."""
import asyncio
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from app.database import engine, SessionLocal, Base
from app.models import Paciente, Prontuario, Triagem, ConfigLLM

PACIENTES = [
    {"cpf": "123.456.789-00", "nome": "Maria Silva Santos", "data_nascimento": "1985-03-15", "sexo": "F", "telefone": "(11) 99999-0001", "email": "maria@email.com"},
    {"cpf": "234.567.890-11", "nome": "João Pedro Oliveira", "data_nascimento": "1972-07-22", "sexo": "M", "telefone": "(11) 99999-0002", "email": "joao@email.com"},
    {"cpf": "345.678.901-22", "nome": "Ana Beatriz Costa", "data_nascimento": "1990-11-08", "sexo": "F", "telefone": "(11) 99999-0003", "email": "ana@email.com"},
    {"cpf": "456.789.012-33", "nome": "Carlos Eduardo Lima", "data_nascimento": "1968-01-30", "sexo": "M", "telefone": "(11) 99999-0004", "email": "carlos@email.com"},
    {"cpf": "567.890.123-44", "nome": "Fernanda Rodrigues", "data_nascimento": "1995-06-12", "sexo": "F", "telefone": "(11) 99999-0005", "email": "fernanda@email.com"},
]

PRONTUARIOS = [
    {"paciente_id": 1, "diagnostico": "Hipertensão arterial sistêmica", "medicamentos": "Losartana 50mg 1x/dia", "alergias": "Dipirona", "observacoes": "Acompanhamento mensal", "medico_responsavel": "Dr. Roberto Mendes"},
    {"paciente_id": 1, "diagnostico": "Diabetes mellitus tipo 2", "medicamentos": "Metformina 850mg 2x/dia", "alergias": "Dipirona", "observacoes": "HbA1c: 7.2%", "medico_responsavel": "Dra. Patrícia Souza"},
    {"paciente_id": 2, "diagnostico": "Lombalgia crônica", "medicamentos": "Paracetamol 750mg SOS", "alergias": "Nenhuma conhecida", "observacoes": "Encaminhado para fisioterapia", "medico_responsavel": "Dr. André Martins"},
    {"paciente_id": 3, "diagnostico": "Asma brônquica moderada", "medicamentos": "Budesonida/Formoterol 200/6mcg 2x/dia", "alergias": "AAS", "observacoes": "Espirometria anual", "medico_responsavel": "Dra. Camila Ferreira"},
    {"paciente_id": 4, "diagnostico": "Insuficiência cardíaca NYHA II", "medicamentos": "Carvedilol 25mg 2x/dia, Enalapril 10mg 2x/dia, Furosemida 40mg 1x/dia", "alergias": "Penicilina", "observacoes": "Ecocardiograma semestral. FE: 40%", "medico_responsavel": "Dr. Roberto Mendes"},
]

TRIAGENS = [
    {"paciente_id": 2, "sintomas": "Dor lombar intensa há 3 dias, piora ao movimento", "classificacao_risco": "amarelo", "pressao_arterial": "140/90", "temperatura": 36.8, "frequencia_cardiaca": 88, "saturacao": 98, "orientacao_ia": "Avaliar sinais de alarme. Solicitar exames de imagem se não melhora."},
    {"paciente_id": 5, "sintomas": "Febre alta, tosse produtiva, dor torácica ao respirar", "classificacao_risco": "laranja", "pressao_arterial": "110/70", "temperatura": 39.2, "frequencia_cardiaca": 110, "saturacao": 93, "orientacao_ia": "Suspeita de pneumonia. Solicitar RX tórax e hemograma urgente."},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # Pacientes
        for p in PACIENTES:
            db.add(Paciente(**p))
        await db.commit()

        # Prontuários
        for p in PRONTUARIOS:
            db.add(Prontuario(**p))
        await db.commit()

        # Triagens
        for t in TRIAGENS:
            db.add(Triagem(**t))
        await db.commit()

        # Config LLM padrão
        db.add(ConfigLLM(
            provider="openai", model_name="gpt-4o-mini",
            temperature=0.7, max_tokens=2048,
            tts_engine="piper", stt_engine="vosk", ativo=True,
        ))
        await db.commit()

    print("Seed concluído com sucesso!")


if __name__ == "__main__":
    asyncio.run(seed())
