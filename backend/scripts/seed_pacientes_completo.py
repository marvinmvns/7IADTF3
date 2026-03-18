"""Seed completo: 25 pacientes com prontuários e triagens realistas.
Doenças alinhadas com o dataset de fine-tuning (512 entradas, 77 doenças).
Todos os dados são SINTÉTICOS — nenhum dado real de pacientes."""
import asyncio
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from app.database import engine, SessionLocal, Base
from app.models import Paciente, Prontuario, Triagem

PACIENTES = [
    # 1-5: já existem no seed original
    # 6+: novos pacientes
    {"cpf": "678.901.234-55", "nome": "Ricardo Almeida Souza", "data_nascimento": "1955-04-18", "sexo": "M", "telefone": "(11) 98765-0006", "email": "ricardo@email.com"},
    {"cpf": "789.012.345-66", "nome": "Lucia Helena Ferreira", "data_nascimento": "1948-09-25", "sexo": "F", "telefone": "(11) 98765-0007", "email": "lucia@email.com"},
    {"cpf": "890.123.456-77", "nome": "Pedro Henrique Barbosa", "data_nascimento": "1982-12-03", "sexo": "M", "telefone": "(21) 98765-0008", "email": "pedro@email.com"},
    {"cpf": "901.234.567-88", "nome": "Camila de Souza Martins", "data_nascimento": "1975-06-14", "sexo": "F", "telefone": "(21) 98765-0009", "email": "camila@email.com"},
    {"cpf": "012.345.678-99", "nome": "Antonio José da Silva", "data_nascimento": "1960-02-28", "sexo": "M", "telefone": "(31) 98765-0010", "email": "antonio@email.com"},
    {"cpf": "111.222.333-44", "nome": "Juliana Pereira Lima", "data_nascimento": "1992-08-07", "sexo": "F", "telefone": "(31) 98765-0011", "email": "juliana@email.com"},
    {"cpf": "222.333.444-55", "nome": "Marcos Vinícius Rocha", "data_nascimento": "1988-01-19", "sexo": "M", "telefone": "(41) 98765-0012", "email": "marcos@email.com"},
    {"cpf": "333.444.555-66", "nome": "Beatriz Santos Oliveira", "data_nascimento": "1970-05-30", "sexo": "F", "telefone": "(41) 98765-0013", "email": "beatriz@email.com"},
    {"cpf": "444.555.666-77", "nome": "Roberto Carlos Mendes", "data_nascimento": "1965-11-12", "sexo": "M", "telefone": "(51) 98765-0014", "email": "roberto@email.com"},
    {"cpf": "555.666.777-88", "nome": "Patricia Andrade Costa", "data_nascimento": "1998-03-22", "sexo": "F", "telefone": "(51) 98765-0015", "email": "patricia@email.com"},
    {"cpf": "666.777.888-99", "nome": "José Maria Nascimento", "data_nascimento": "1952-07-08", "sexo": "M", "telefone": "(61) 98765-0016", "email": "jose@email.com"},
    {"cpf": "777.888.999-00", "nome": "Sandra Regina Moreira", "data_nascimento": "1980-10-15", "sexo": "F", "telefone": "(61) 98765-0017", "email": "sandra@email.com"},
    {"cpf": "888.999.000-11", "nome": "Felipe Augusto Ribeiro", "data_nascimento": "2000-04-01", "sexo": "M", "telefone": "(71) 98765-0018", "email": "felipe@email.com"},
    {"cpf": "999.000.111-22", "nome": "Gabriela Cristina Dias", "data_nascimento": "1993-12-25", "sexo": "F", "telefone": "(71) 98765-0019", "email": "gabriela@email.com"},
    {"cpf": "100.200.300-40", "nome": "Eduardo Farias Gomes", "data_nascimento": "1958-08-16", "sexo": "M", "telefone": "(81) 98765-0020", "email": "eduardo@email.com"},
    {"cpf": "200.300.400-50", "nome": "Mariana Lopes Cardoso", "data_nascimento": "1987-02-10", "sexo": "F", "telefone": "(81) 98765-0021", "email": "mariana@email.com"},
    {"cpf": "300.400.500-60", "nome": "Thiago Ramos Teixeira", "data_nascimento": "1978-09-05", "sexo": "M", "telefone": "(85) 98765-0022", "email": "thiago@email.com"},
    {"cpf": "400.500.600-70", "nome": "Isabela Carvalho Pinto", "data_nascimento": "1996-06-30", "sexo": "F", "telefone": "(85) 98765-0023", "email": "isabela@email.com"},
    {"cpf": "500.600.700-80", "nome": "Oswaldo Pires Neto", "data_nascimento": "1945-03-12", "sexo": "M", "telefone": "(91) 98765-0024", "email": "oswaldo@email.com"},
    {"cpf": "600.700.800-90", "nome": "Renata Vieira Sampaio", "data_nascimento": "1983-11-28", "sexo": "F", "telefone": "(91) 98765-0025", "email": "renata@email.com"},
]

# Prontuários: doenças alinhadas com as 77 do dataset
# paciente_id será calculado: existentes (1-5) + novos (offset)
PRONTUARIOS_NOVOS = [
    # Ricardo (6) - Diabético + DPOC
    {"offset": 0, "diagnostico": "Diabetes mellitus tipo 2", "medicamentos": "Metformina 850mg 2x/dia, Glicazida 30mg 1x/dia", "alergias": "Sulfonamidas", "observacoes": "HbA1c: 8.1%. Neuropatia periférica em investigação", "medico_responsavel": "Dra. Patrícia Souza"},
    {"offset": 0, "diagnostico": "DPOC Gold II", "medicamentos": "Tiotrópio 18mcg 1x/dia, Salbutamol SOS", "alergias": "Sulfonamidas", "observacoes": "Ex-tabagista 40 anos/maço. Espirometria: VEF1 65%", "medico_responsavel": "Dr. André Martins"},
    # Lucia (7) - Alzheimer + Osteoporose + Hipertensão
    {"offset": 1, "diagnostico": "Doença de Alzheimer - fase moderada", "medicamentos": "Donepezila 10mg 1x/dia, Memantina 20mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "MEEM: 18/30. Cuidadora presente. Desorientação temporal", "medico_responsavel": "Dr. Roberto Mendes"},
    {"offset": 1, "diagnostico": "Osteoporose", "medicamentos": "Alendronato 70mg 1x/semana, Cálcio+VitD", "alergias": "Nenhuma conhecida", "observacoes": "Densitometria: T-score -3.2 colo femoral", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 1, "diagnostico": "Hipertensão arterial sistêmica", "medicamentos": "Anlodipino 5mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "PA controlada", "medico_responsavel": "Dr. Roberto Mendes"},
    # Pedro (8) - Epilepsia
    {"offset": 2, "diagnostico": "Epilepsia focal - lobo temporal", "medicamentos": "Carbamazepina 400mg 2x/dia", "alergias": "Fenitoína", "observacoes": "Última crise há 6 meses. EEG com foco temporal esquerdo", "medico_responsavel": "Dr. André Martins"},
    # Camila (9) - Lúpus + Artrite reumatoide
    {"offset": 3, "diagnostico": "Lúpus eritematoso sistêmico", "medicamentos": "Hidroxicloroquina 400mg 1x/dia, Prednisona 10mg 1x/dia", "alergias": "Ibuprofeno", "observacoes": "FAN+, Anti-DNA+. Nefrite lúpica classe III", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 3, "diagnostico": "Artrite reumatoide", "medicamentos": "Metotrexato 15mg 1x/semana, Ácido fólico 5mg", "alergias": "Ibuprofeno", "observacoes": "FR+ PCR elevado. Comprometimento de pequenas articulações", "medico_responsavel": "Dra. Camila Ferreira"},
    # Antonio (10) - Parkinson + Depressão
    {"offset": 4, "diagnostico": "Doença de Parkinson", "medicamentos": "Levodopa/Carbidopa 250/25mg 3x/dia, Pramipexol 0.5mg 3x/dia", "alergias": "AAS", "observacoes": "Hoehn & Yahr estágio 2. Tremor de repouso em MSD", "medico_responsavel": "Dr. Roberto Mendes"},
    {"offset": 4, "diagnostico": "Depressão maior", "medicamentos": "Sertralina 100mg 1x/dia", "alergias": "AAS", "observacoes": "PHQ-9: 15. Acompanhamento psiquiátrico mensal", "medico_responsavel": "Dra. Patrícia Souza"},
    # Juliana (11) - Endometriose + Ansiedade
    {"offset": 5, "diagnostico": "Endometriose profunda", "medicamentos": "Dienogeste 2mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "RM: lesão em septo retovaginal. Dismenorreia intensa", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 5, "diagnostico": "Transtorno de ansiedade generalizada", "medicamentos": "Escitalopram 10mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "GAD-7: 12. Psicoterapia cognitivo-comportamental", "medico_responsavel": "Dra. Patrícia Souza"},
    # Marcos (12) - Hepatite C + Cirrose
    {"offset": 6, "diagnostico": "Hepatite C crônica", "medicamentos": "Sofosbuvir/Velpatasvir 400/100mg 1x/dia (12 semanas)", "alergias": "Nenhuma conhecida", "observacoes": "Genótipo 1a. Carga viral: 1.2M UI/mL", "medico_responsavel": "Dr. André Martins"},
    {"offset": 6, "diagnostico": "Cirrose hepática Child-Pugh A", "medicamentos": "Espironolactona 100mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Fibroscan: F4. Varizes esofágicas pequenas", "medico_responsavel": "Dr. André Martins"},
    # Beatriz (13) - Câncer de mama + Trombose
    {"offset": 7, "diagnostico": "Câncer de mama - EC IIA (T2N0M0)", "medicamentos": "Tamoxifeno 20mg 1x/dia", "alergias": "Contraste iodado", "observacoes": "Pós-mastectomia com reconstrução. RE+/PR+/HER2-. QT adjuvante concluída", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 7, "diagnostico": "Trombose venosa profunda - MIE", "medicamentos": "Rivaroxabana 20mg 1x/dia", "alergias": "Contraste iodado", "observacoes": "TVP poplítea pós-cirúrgica. Doppler de controle em 3 meses", "medico_responsavel": "Dr. Roberto Mendes"},
    # Roberto (14) - Infarto prévio + Arritmia
    {"offset": 8, "diagnostico": "Infarto agudo do miocárdio prévio (parede anterior)", "medicamentos": "AAS 100mg, Clopidogrel 75mg, Atorvastatina 80mg, Metoprolol 50mg 2x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Angioplastia com stent em DA há 8 meses. FE: 45%", "medico_responsavel": "Dr. Roberto Mendes"},
    {"offset": 8, "diagnostico": "Fibrilação atrial paroxística", "medicamentos": "Amiodarona 200mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Holter: episódios de FA. CHA2DS2-VASc: 3", "medico_responsavel": "Dr. Roberto Mendes"},
    # Patricia (15) - Dengue (recente) + Anemia
    {"offset": 9, "diagnostico": "Dengue - sorotipo 2 (alta recente)", "medicamentos": "Hidratação oral", "alergias": "Dipirona", "observacoes": "NS1+. Plaquetas nadir 48.000. Recuperada", "medico_responsavel": "Dr. André Martins"},
    {"offset": 9, "diagnostico": "Anemia ferropriva", "medicamentos": "Sulfato ferroso 300mg 2x/dia", "alergias": "Dipirona", "observacoes": "Hb: 9.8, Ferritina: 8. Investigar sangramento", "medico_responsavel": "Dra. Patrícia Souza"},
    # José (16) - Câncer pulmão + Embolia
    {"offset": 10, "diagnostico": "Adenocarcinoma de pulmão - EC IIIA", "medicamentos": "Pembrolizumab 200mg IV q3semanas", "alergias": "Nenhuma conhecida", "observacoes": "PD-L1 80%. TC: massa em LSE 4.5cm. Linfonodos mediastinais+", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 10, "diagnostico": "Embolia pulmonar subsegmentar", "medicamentos": "Enoxaparina 60mg SC 2x/dia", "alergias": "Nenhuma conhecida", "observacoes": "AngioTC: EP subsegmentar em LID. D-dímero: 4500", "medico_responsavel": "Dr. Roberto Mendes"},
    # Sandra (17) - Fibromialgia + Hipotireoidismo
    {"offset": 11, "diagnostico": "Fibromialgia", "medicamentos": "Duloxetina 60mg 1x/dia, Pregabalina 75mg 2x/dia", "alergias": "Nenhuma conhecida", "observacoes": "11/18 tender points. Distúrbio do sono associado", "medico_responsavel": "Dra. Patrícia Souza"},
    {"offset": 11, "diagnostico": "Hipotireoidismo", "medicamentos": "Levotiroxina 75mcg 1x/dia em jejum", "alergias": "Nenhuma conhecida", "observacoes": "TSH: 0.8 (controlado). Anti-TPO+", "medico_responsavel": "Dr. André Martins"},
    # Felipe (18) - TDAH + Gastrite
    {"offset": 12, "diagnostico": "TDAH - predominantemente desatento", "medicamentos": "Metilfenidato 20mg 2x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Diagnóstico na adolescência. Acompanhamento psiquiátrico", "medico_responsavel": "Dra. Patrícia Souza"},
    {"offset": 12, "diagnostico": "Gastrite erosiva", "medicamentos": "Omeprazol 20mg 1x/dia, Sucralfato 1g 3x/dia", "alergias": "Nenhuma conhecida", "observacoes": "EDA: gastrite erosiva antral. H.pylori negativo", "medico_responsavel": "Dr. André Martins"},
    # Gabriela (19) - Diabetes gestacional
    {"offset": 13, "diagnostico": "Diabetes mellitus gestacional", "medicamentos": "Insulina NPH 10UI à noite", "alergias": "Nenhuma conhecida", "observacoes": "IG: 28 semanas. GTT alterado. Glicemia capilar 4x/dia", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 13, "diagnostico": "Pré-eclâmpsia leve", "medicamentos": "Metildopa 250mg 3x/dia, AAS 100mg", "alergias": "Nenhuma conhecida", "observacoes": "PA: 150/95. Proteinúria: 350mg/24h. Repouso relativo", "medico_responsavel": "Dra. Camila Ferreira"},
    # Eduardo (20) - AVC + Esquizofrenia
    {"offset": 14, "diagnostico": "AVC isquêmico (ACM direita) - sequela", "medicamentos": "AAS 100mg, Atorvastatina 40mg, Losartana 50mg", "alergias": "Penicilina", "observacoes": "Hemiparesia esquerda grau 3. Fonoaudiologia + fisioterapia", "medico_responsavel": "Dr. Roberto Mendes"},
    # Mariana (21) - Esclerose múltipla
    {"offset": 15, "diagnostico": "Esclerose múltipla surto-remissão", "medicamentos": "Fingolimode 0.5mg 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "RM: 8 lesões periventriculares. Último surto há 4 meses (neurite óptica)", "medico_responsavel": "Dr. André Martins"},
    # Thiago (22) - Pancreatite + Obesidade
    {"offset": 16, "diagnostico": "Pancreatite crônica", "medicamentos": "Enzimas pancreáticas 25.000UI 3x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Etiologia alcoólica. Calcificações pancreáticas à TC. Abstinência há 2 anos", "medico_responsavel": "Dr. André Martins"},
    {"offset": 16, "diagnostico": "Obesidade grau II (IMC 37)", "medicamentos": "Liraglutida 1.8mg SC 1x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Acompanhamento nutricional. Meta: perda de 15%", "medico_responsavel": "Dra. Patrícia Souza"},
    # Isabela (23) - Psoriase + Dermatite
    {"offset": 17, "diagnostico": "Psoríase em placas - moderada", "medicamentos": "Metotrexato 15mg 1x/semana, Ácido fólico", "alergias": "Nenhuma conhecida", "observacoes": "PASI: 12. Placas em couro cabeludo, cotovelos e joelhos", "medico_responsavel": "Dra. Camila Ferreira"},
    {"offset": 17, "diagnostico": "Dermatite atópica", "medicamentos": "Tacrolimo 0.1% tópico 2x/dia", "alergias": "Nenhuma conhecida", "observacoes": "Desde infância. Exacerbação em meses secos", "medico_responsavel": "Dra. Camila Ferreira"},
    # Oswaldo (24) - Glaucoma + Catarata + Insuficiência renal
    {"offset": 18, "diagnostico": "Glaucoma primário de ângulo aberto", "medicamentos": "Timolol 0.5% colírio 2x/dia, Latanoprosta colírio à noite", "alergias": "AAS", "observacoes": "PIO: OD 14, OE 16 (controlada). Campo visual com escotoma arciforme OD", "medico_responsavel": "Dr. André Martins"},
    {"offset": 18, "diagnostico": "Catarata senil bilateral", "medicamentos": "Nenhum", "alergias": "AAS", "observacoes": "Acuidade visual: OD 20/60, OE 20/80. Cirurgia programada OE", "medico_responsavel": "Dr. André Martins"},
    {"offset": 18, "diagnostico": "Doença renal crônica estágio 3b", "medicamentos": "Eritropoietina 4000UI SC 3x/semana", "alergias": "AAS", "observacoes": "TFG: 38mL/min. Creatinina: 2.1. Acompanhamento nefrológico", "medico_responsavel": "Dr. Roberto Mendes"},
    # Renata (25) - Meningite (recente) + Cefaleia
    {"offset": 19, "diagnostico": "Meningite bacteriana (pneumocócica) - tratada", "medicamentos": "Ceftriaxona 2g IV 14 dias (concluído)", "alergias": "Nenhuma conhecida", "observacoes": "LCR: pleocitose neutrofílica, proteína 380. Cultura: S. pneumoniae. Alta hospitalar", "medico_responsavel": "Dr. André Martins"},
    {"offset": 19, "diagnostico": "Cefaleia pós-meningite", "medicamentos": "Paracetamol 750mg SOS", "alergias": "Nenhuma conhecida", "observacoes": "RM crânio sem alterações residuais. Seguimento ambulatorial", "medico_responsavel": "Dr. André Martins"},
]

# Triagens variadas
TRIAGENS_NOVAS = [
    {"offset": 0, "sintomas": "Polidipsia, poliúria, visão turva, glicemia capilar 380mg/dL", "classificacao_risco": "laranja", "pressao_arterial": "150/95", "temperatura": 36.5, "frequencia_cardiaca": 100, "saturacao": 97, "orientacao_ia": "Hiperglicemia grave. Avaliar cetoacidose. HGT seriado, gasometria."},
    {"offset": 1, "sintomas": "Confusão mental progressiva, não reconhece familiares, agitação", "classificacao_risco": "amarelo", "pressao_arterial": "140/85", "temperatura": 36.8, "frequencia_cardiaca": 78, "saturacao": 96, "orientacao_ia": "Avaliar delirium vs progressão demencial. Excluir causas reversíveis."},
    {"offset": 3, "sintomas": "Dor articular difusa, rash malar, fadiga intensa, febre baixa", "classificacao_risco": "amarelo", "pressao_arterial": "120/75", "temperatura": 37.8, "frequencia_cardiaca": 92, "saturacao": 97, "orientacao_ia": "Flare de LES. Avaliar complemento, anti-DNA, função renal. Ajustar imunossupressão."},
    {"offset": 4, "sintomas": "Tremor intenso bilateral, rigidez, dificuldade para caminhar, queda", "classificacao_risco": "amarelo", "pressao_arterial": "130/80", "temperatura": 36.6, "frequencia_cardiaca": 68, "saturacao": 98, "orientacao_ia": "Avaliar necessidade de ajuste de Levodopa. RX de quadril para excluir fratura."},
    {"offset": 7, "sintomas": "Edema em MIE, dor na panturrilha, empastamento", "classificacao_risco": "laranja", "pressao_arterial": "125/80", "temperatura": 36.7, "frequencia_cardiaca": 88, "saturacao": 98, "orientacao_ia": "Suspeita de TVP. Solicitar Doppler venoso de MIE urgente. Não massagear."},
    {"offset": 8, "sintomas": "Dor torácica retroesternal, sudorese, irradiação para MSE", "classificacao_risco": "vermelho", "pressao_arterial": "90/60", "temperatura": 36.2, "frequencia_cardiaca": 130, "saturacao": 91, "orientacao_ia": "PROTOCOLO IAM. ECG imediato. Troponina. Acesso venoso. Sala de emergência."},
    {"offset": 9, "sintomas": "Febre alta, cefaleia intensa, dor retro-orbital, petéquias", "classificacao_risco": "laranja", "pressao_arterial": "100/65", "temperatura": 39.5, "frequencia_cardiaca": 108, "saturacao": 96, "orientacao_ia": "Dengue com sinais de alarme. Hemograma urgente. Hidratação IV. Prova do laço."},
    {"offset": 10, "sintomas": "Dispneia progressiva, hemoptise, emagrecimento", "classificacao_risco": "laranja", "pressao_arterial": "110/70", "temperatura": 37.2, "frequencia_cardiaca": 95, "saturacao": 92, "orientacao_ia": "Avaliar progressão tumoral vs embolia. AngioTC de tórax. Gasometria arterial."},
    {"offset": 13, "sintomas": "Cefaleia intensa, escotomas visuais, edema de MMII, PA 160/100", "classificacao_risco": "laranja", "pressao_arterial": "160/100", "temperatura": 36.5, "frequencia_cardiaca": 90, "saturacao": 98, "orientacao_ia": "Pré-eclâmpsia grave. Sulfato de magnésio. Avaliação obstétrica urgente."},
    {"offset": 14, "sintomas": "Hemiparesia esquerda súbita, disartria, desvio de rima", "classificacao_risco": "vermelho", "pressao_arterial": "180/110", "temperatura": 36.4, "frequencia_cardiaca": 85, "saturacao": 96, "orientacao_ia": "PROTOCOLO AVC. TC crânio urgente. Tempo é cérebro. Avaliar trombólise."},
    {"offset": 18, "sintomas": "Oligúria, edema generalizado, náusea, confusão leve", "classificacao_risco": "laranja", "pressao_arterial": "170/100", "temperatura": 36.8, "frequencia_cardiaca": 78, "saturacao": 94, "orientacao_ia": "Descompensação de DRC. Gasometria, eletrólitos, ureia/creatinina urgente."},
    {"offset": 19, "sintomas": "Cefaleia holocraniana intensa, rigidez de nuca, febre alta, fotofobia", "classificacao_risco": "vermelho", "pressao_arterial": "130/85", "temperatura": 39.8, "frequencia_cardiaca": 115, "saturacao": 97, "orientacao_ia": "SUSPEITA DE MENINGITE. Hemocultura + LCR urgente. ATB empírica imediata."},
]


async def seed_completo():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # Descobre o maior ID existente de paciente
        from sqlalchemy import select, func
        result = await db.execute(select(func.max(Paciente.id)))
        max_id = result.scalar() or 0
        print(f"Pacientes existentes: {max_id}")

        # Verifica CPFs que já existem
        result = await db.execute(select(Paciente.cpf))
        cpfs_existentes = {row[0] for row in result.all()}

        # Insere novos pacientes
        id_map = {}  # offset -> paciente_id
        inseridos = 0
        for i, p in enumerate(PACIENTES):
            if p["cpf"] in cpfs_existentes:
                # Busca o ID existente
                r = await db.execute(select(Paciente.id).where(Paciente.cpf == p["cpf"]))
                existing_id = r.scalar()
                id_map[i] = existing_id
                print(f"  Paciente {p['nome']} já existe (ID {existing_id})")
                continue
            pac = Paciente(**p)
            db.add(pac)
            await db.flush()
            id_map[i] = pac.id
            inseridos += 1
        await db.commit()
        print(f"Pacientes inseridos: {inseridos}")

        # Insere prontuários
        pront_inseridos = 0
        for pr in PRONTUARIOS_NOVOS:
            offset = pr["offset"]
            if offset not in id_map:
                continue
            dados = {k: v for k, v in pr.items() if k != "offset"}
            dados["paciente_id"] = id_map[offset]
            db.add(Prontuario(**dados))
            pront_inseridos += 1
        await db.commit()
        print(f"Prontuários inseridos: {pront_inseridos}")

        # Insere triagens
        tri_inseridos = 0
        for tr in TRIAGENS_NOVAS:
            offset = tr["offset"]
            if offset not in id_map:
                continue
            dados = {k: v for k, v in tr.items() if k != "offset"}
            dados["paciente_id"] = id_map[offset]
            db.add(Triagem(**dados))
            tri_inseridos += 1
        await db.commit()
        print(f"Triagens inseridas: {tri_inseridos}")

    print(f"\nSeed completo! {inseridos} pacientes, {pront_inseridos} prontuários, {tri_inseridos} triagens")


if __name__ == "__main__":
    asyncio.run(seed_completo())
