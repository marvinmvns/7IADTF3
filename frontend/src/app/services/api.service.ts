import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Paciente, FichaPaciente, Prontuario, Triagem, Mensagem, ConfigLLM, DadoMedico, ModeloFineTuning, FineTuningJob, DatasetEntry } from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = '/api';

  constructor(private http: HttpClient) {}

  // Pacientes
  buscarPorCpf(cpf: string): Observable<Paciente> {
    return this.http.get<Paciente>(`${this.base}/pacientes/cpf/${cpf}`);
  }

  fichaCompleta(cpf: string): Observable<FichaPaciente> {
    return this.http.get<FichaPaciente>(`${this.base}/pacientes/cpf/${cpf}/ficha`);
  }

  listarPacientes(): Observable<Paciente[]> {
    return this.http.get<Paciente[]>(`${this.base}/pacientes/`);
  }

  criarPaciente(dados: Partial<Paciente>): Observable<Paciente> {
    return this.http.post<Paciente>(`${this.base}/pacientes/`, dados);
  }

  atualizarPaciente(id: number, dados: Partial<Paciente>): Observable<Paciente> {
    return this.http.put<Paciente>(`${this.base}/pacientes/${id}`, dados);
  }

  removerPaciente(id: number): Observable<any> {
    return this.http.delete(`${this.base}/pacientes/${id}`);
  }

  buscarCep(cep: string): Observable<any> {
    return this.http.get(`${this.base}/pacientes/cep-lookup/${cep}`);
  }

  // Prontuários
  criarProntuario(dados: Partial<Prontuario>): Observable<Prontuario> {
    return this.http.post<Prontuario>(`${this.base}/prontuarios/`, dados);
  }

  // Triagem
  criarTriagem(dados: Partial<Triagem>): Observable<Triagem> {
    return this.http.post<Triagem>(`${this.base}/triagens/`, dados);
  }

  validarTriagem(id: number): Observable<Triagem> {
    return this.http.patch<Triagem>(`${this.base}/triagens/${id}/validar`, {});
  }

  // Chat
  enviarMensagem(conteudo: string, conversaId?: number, pacienteId?: number, tipo = 'geral'): Observable<Mensagem> {
    return this.http.post<Mensagem>(`${this.base}/chat/mensagem`, {
      conteudo, conversa_id: conversaId, paciente_id: pacienteId, tipo,
    });
  }

  enviarMensagemStream(conteudo: string, conversaId?: number, pacienteId?: number, tipo = 'geral',
                       medicoNome?: string, medicoCrm?: string): {
    start: (onToken: (t: string) => void, onDone: (data: any) => void, onError: (e: string) => void, onThinking?: () => void) => void
  } {
    return {
      start: (onToken, onDone, onError, onThinking?) => {
        fetch(`${this.base}/chat/mensagem-stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conteudo, conversa_id: conversaId, paciente_id: pacienteId, tipo,
                                 medico_nome: medicoNome, medico_crm: medicoCrm }),
        }).then(async (resp) => {
          const reader = resp.body?.getReader();
          const decoder = new TextDecoder();
          if (!reader) { onError('Sem resposta'); return; }
          let buffer = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (data.thinking) { onThinking?.(); }
                  else if (data.token) onToken(data.token);
                  else if (data.done) onDone(data);
                  else if (data.error) onError(data.error);
                } catch {}
              }
            }
          }
        }).catch((e) => onError(e.message));
      }
    };
  }

  vozParaTexto(audio: Blob): Observable<{ texto: string }> {
    const form = new FormData();
    form.append('audio', audio, 'audio.wav');
    return this.http.post<{ texto: string }>(`${this.base}/chat/voz-para-texto`, form);
  }

  textoParaVoz(texto: string): Observable<Blob> {
    return this.http.post(`${this.base}/chat/texto-para-voz?texto=${encodeURIComponent(texto)}`, {}, { responseType: 'blob' });
  }

  // Config
  obterConfig(): Observable<ConfigLLM> {
    return this.http.get<ConfigLLM>(`${this.base}/config/llm`);
  }

  salvarConfig(dados: Partial<ConfigLLM>): Observable<ConfigLLM> {
    return this.http.post<ConfigLLM>(`${this.base}/config/llm`, dados);
  }

  // Scraping
  agenteInteligente(tema: string): Observable<any> {
    return this.http.post(`${this.base}/scraping/agente-inteligente?tema=${encodeURIComponent(tema)}`, {});
  }

  buscarDados(fonte: string, termo: string, max = 10): Observable<DadoMedico[]> {
    return this.http.post<DadoMedico[]>(`${this.base}/scraping/buscar`, { fonte, termo, max_resultados: max });
  }

  buscarTodasFontes(termo: string): Observable<DadoMedico[]> {
    return this.http.post<DadoMedico[]>(`${this.base}/scraping/buscar-todas?termo=${encodeURIComponent(termo)}`, {});
  }

  scrapingUrlLivre(url: string): Observable<any> {
    return this.http.post(`${this.base}/scraping/url-livre?url=${encodeURIComponent(url)}`, {});
  }

  enviarParaDataset(termo: string): Observable<any> {
    return this.http.post(`${this.base}/scraping/enviar-para-dataset?termo=${encodeURIComponent(termo)}`, {});
  }

  executarAgente(termo: string): Observable<any> {
    return this.http.post(`${this.base}/scraping/agente?termo=${encodeURIComponent(termo)}`, {});
  }

  listarDados(fonte?: string): Observable<DadoMedico[]> {
    const params = fonte ? `?fonte=${fonte}` : '';
    return this.http.get<DadoMedico[]>(`${this.base}/scraping/dados${params}`);
  }

  // Fine-Tuning
  listarModelosFT(): Observable<ModeloFineTuning[]> {
    return this.http.get<ModeloFineTuning[]>(`${this.base}/finetuning/modelos`);
  }

  iniciarFineTuning(config: any): Observable<FineTuningJob> {
    return this.http.post<FineTuningJob>(`${this.base}/finetuning/iniciar`, config);
  }

  listarJobs(): Observable<FineTuningJob[]> {
    return this.http.get<FineTuningJob[]>(`${this.base}/finetuning/jobs`);
  }

  obterJob(id: number): Observable<FineTuningJob> {
    return this.http.get<FineTuningJob>(`${this.base}/finetuning/jobs/${id}`);
  }

  cancelarJob(id: number): Observable<any> {
    return this.http.post(`${this.base}/finetuning/jobs/${id}/cancelar`, {});
  }

  listarDataset(): Observable<DatasetEntry[]> {
    return this.http.get<DatasetEntry[]>(`${this.base}/finetuning/dataset`);
  }

  adicionarDatasetEntry(entry: any): Observable<DatasetEntry> {
    return this.http.post<DatasetEntry>(`${this.base}/finetuning/dataset`, entry);
  }

  removerDatasetEntry(id: number): Observable<any> {
    return this.http.delete(`${this.base}/finetuning/dataset/${id}`);
  }

  importarDatasetJSON(): Observable<any> {
    return this.http.post(`${this.base}/finetuning/dataset/importar-json`, {});
  }

  datasetStats(): Observable<any> {
    return this.http.get(`${this.base}/finetuning/dataset/stats`);
  }

  listarModelosOllama(): Observable<any> {
    return this.http.get(`${this.base}/config/ollama/modelos`);
  }

  listarModelosOpenAI(): Observable<any> {
    return this.http.get(`${this.base}/config/openai/modelos`);
  }

  listarModelosLlamaCpp(): Observable<any> {
    return this.http.get(`${this.base}/config/llama-cpp/modelos`);
  }

  listarModelosFinetuned(): Observable<any> {
    return this.http.get(`${this.base}/config/finetuned/modelos`);
  }

  gpuInfo(): Observable<any> {
    return this.http.get(`${this.base}/config/gpu/info`);
  }

  // llama-server management
  statusLlamaServer(): Observable<any> {
    return this.http.get(`${this.base}/config/llama-server/status`);
  }

  trocarModelo(modelo: string): Observable<any> {
    return this.http.post(`${this.base}/config/llama-server/trocar-modelo?modelo=${encodeURIComponent(modelo)}`, {});
  }

  pararLlamaServer(): Observable<any> {
    return this.http.post(`${this.base}/config/llama-server/stop`, {});
  }

  iniciarLlamaServer(): Observable<any> {
    return this.http.post(`${this.base}/config/llama-server/start`, {});
  }

  gerarDatasetDoenca(doenca: string): Observable<any> {
    return this.http.post(`${this.base}/finetuning/dataset/gerar?doenca=${encodeURIComponent(doenca)}`, {});
  }

  // Auditoria
  listarLogs(acao?: string, skip = 0, limit = 100): Observable<any[]> {
    let params = `?skip=${skip}&limit=${limit}`;
    if (acao) params += `&acao=${encodeURIComponent(acao)}`;
    return this.http.get<any[]>(`${this.base}/auditoria/logs${params}`);
  }

  statsAuditoria(): Observable<any> {
    return this.http.get(`${this.base}/auditoria/stats`);
  }

  categoriasAuditoria(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/auditoria/categorias`);
  }

  // RAG
  indexarRAG(): Observable<any> {
    return this.http.post(`${this.base}/rag/indexar`, {});
  }

  ragStats(): Observable<any> {
    return this.http.get(`${this.base}/rag/stats`);
  }

  buscarRAG(pergunta: string, n: number = 5): Observable<any> {
    return this.http.get(`${this.base}/rag/buscar?pergunta=${encodeURIComponent(pergunta)}&n=${n}`);
  }
}
