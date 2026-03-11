import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Paciente, FichaPaciente, Prontuario, Triagem, Mensagem, ConfigLLM, DadoMedico } from '../models/models';

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

  criarPaciente(dados: Partial<Paciente>): Observable<Paciente> {
    return this.http.post<Paciente>(`${this.base}/pacientes/`, dados);
  }

  // Prontuários
  criarProntuario(dados: Partial<Prontuario>): Observable<Prontuario> {
    return this.http.post<Prontuario>(`${this.base}/prontuarios/`, dados);
  }

  // Triagem
  criarTriagem(dados: Partial<Triagem>): Observable<Triagem> {
    return this.http.post<Triagem>(`${this.base}/triagens/`, dados);
  }

  // Chat
  enviarMensagem(conteudo: string, conversaId?: number, pacienteId?: number, tipo = 'geral'): Observable<Mensagem> {
    return this.http.post<Mensagem>(`${this.base}/chat/mensagem`, {
      conteudo, conversa_id: conversaId, paciente_id: pacienteId, tipo,
    });
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
  buscarDados(fonte: string, termo: string, max = 10): Observable<DadoMedico[]> {
    return this.http.post<DadoMedico[]>(`${this.base}/scraping/buscar`, { fonte, termo, max_resultados: max });
  }

  executarAgente(termo: string): Observable<any> {
    return this.http.post(`${this.base}/scraping/agente?termo=${encodeURIComponent(termo)}`, {});
  }

  listarDados(fonte?: string): Observable<DadoMedico[]> {
    const params = fonte ? `?fonte=${fonte}` : '';
    return this.http.get<DadoMedico[]>(`${this.base}/scraping/dados${params}`);
  }
}
