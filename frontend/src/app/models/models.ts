export interface Paciente {
  id: number;
  cpf: string;
  nome: string;
  data_nascimento: string;
  sexo: string;
  telefone?: string;
  email?: string;
  cep?: string;
  endereco?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  criado_em: string;
}

export interface Prontuario {
  id: number;
  paciente_id: number;
  diagnostico: string;
  medicamentos?: string;
  alergias?: string;
  observacoes?: string;
  medico_responsavel: string;
  data_consulta: string;
  criado_em: string;
}

export interface Triagem {
  id: number;
  paciente_id: number;
  sintomas: string;
  classificacao_risco: string;
  pressao_arterial?: string;
  temperatura?: number;
  frequencia_cardiaca?: number;
  saturacao?: number;
  orientacao_ia?: string;
  nivel_urgencia?: number;
  diagnosticos_possiveis?: string;
  validado_por_humano: boolean;
  criado_em: string;
}

export interface Mensagem {
  id: number;
  conversa_id: number;
  papel: string;
  conteudo: string;
  fonte?: string;
  criado_em: string;
}

export interface Conversa {
  id: number;
  paciente_id?: number;
  tipo: string;
  criado_em: string;
  mensagens: Mensagem[];
}

export interface FichaPaciente {
  paciente: Paciente;
  prontuarios: Prontuario[];
  triagens: Triagem[];
  conversas: Conversa[];
}

export interface ConfigLLM {
  id: number;
  provider: string;
  model_name: string;
  base_url?: string;
  temperature: number;
  max_tokens: number;
  tts_engine: string;
  stt_engine: string;
  ativo: boolean;
  atualizado_em: string;
}

export interface DadoMedico {
  id: number;
  fonte: string;
  titulo: string;
  conteudo: string;
  url: string;
  categoria?: string;
  coletado_em: string;
}

export interface ModeloFineTuning {
  id: string;
  nome: string;
  parametros: string;
  descricao: string;
  ram_estimada: string;
  vram_treino?: string;
  dispositivo?: string;
}

export interface FineTuningJob {
  id: number;
  modelo_base: string;
  status: string;
  progresso: number;
  epoca_atual: number;
  epocas_total: number;
  loss_atual?: number;
  learning_rate: number;
  lora_r: number;
  lora_alpha: number;
  batch_size: number;
  max_length: number;
  dataset_size: number;
  erro_msg?: string;
  caminho_modelo?: string;
  logs?: string;
  iniciado_em?: string;
  concluido_em?: string;
  criado_em: string;
}

export interface DatasetEntry {
  id: number;
  pergunta: string;
  contexto?: string;
  resposta: string;
  categoria?: string;
  ativo: boolean;
  criado_em: string;
}
