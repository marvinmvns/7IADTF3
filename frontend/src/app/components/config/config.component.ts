import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ConfigLLM } from '../../models/models';

@Component({
  selector: 'app-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle;">settings</span>
        Configuração do LLM e TTS/STT
      </h2>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        <!-- LLM -->
        <div>
          <h3 style="font-size: 15px; margin-bottom: 12px; color: var(--primary);">Modelo de Linguagem (LLM)</h3>
          <div class="form-group">
            <label>Provider</label>
            <select class="form-control" [(ngModel)]="config.provider" (ngModelChange)="onProviderChange()">
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="llama-cpp">llama.cpp SYCL (Intel GPU)</option>
              <option value="finetuned">Fine-Tuned (Modelo Treinado)</option>
            </select>
          </div>

          <!-- OpenAI -->
          @if (config.provider === 'openai') {
            <div class="form-group">
              <label>API Key</label>
              <input class="form-control" type="password" [(ngModel)]="apiKey" placeholder="sk-..."
                     (blur)="carregarModelosOpenAI()">
            </div>
            <div class="form-group">
              <label>Modelo</label>
              @if (modelosOpenAI.length > 0) {
                <select class="form-control" [(ngModel)]="config.model_name">
                  @for (m of modelosOpenAI; track m.name) {
                    <option [value]="m.name">{{ m.name }}</option>
                  }
                </select>
              } @else {
                <input class="form-control" [(ngModel)]="config.model_name" placeholder="gpt-4o-mini">
              }
            </div>
            <div style="padding: 8px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 12px;"
                 [style.background]="openaiStatus === 'online' ? '#e8f5e9' : openaiStatus === 'sem_api_key' ? '#fff3e0' : '#fce4ec'"
                 [style.color]="openaiStatus === 'online' ? 'var(--success)' : openaiStatus === 'sem_api_key' ? 'var(--warning)' : 'var(--danger)'">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">
                {{ openaiStatus === 'online' ? 'check_circle' : openaiStatus === 'sem_api_key' ? 'vpn_key' : 'error' }}
              </span>
              @if (openaiStatus === 'online') {
                OpenAI: {{ modelosOpenAI.length }} modelo(s) disponível(is)
              } @else if (openaiStatus === 'sem_api_key') {
                Insira sua API Key para listar modelos
              } @else if (openaiStatus === 'api_key_invalida') {
                API Key inválida
              } @else if (openaiStatus === 'checking') {
                Verificando...
              } @else {
                OpenAI indisponível
              }
            </div>
          }

          <!-- Ollama -->
          @if (config.provider === 'ollama') {
            <div class="form-group">
              <label>Modelo</label>
              @if (modelosOllama.length > 0) {
                <select class="form-control" [(ngModel)]="config.model_name">
                  @for (m of modelosOllama; track m.name) {
                    <option [value]="m.name">{{ m.name }} ({{ formatSize(m.size) }})</option>
                  }
                </select>
              } @else {
                <input class="form-control" [(ngModel)]="config.model_name" placeholder="qwen2.5:0.5b">
              }
            </div>
            <div class="form-group">
              <label>URL do Ollama</label>
              <input class="form-control" [(ngModel)]="config.base_url" placeholder="http://ollama:11434">
            </div>
            <div style="padding: 8px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 12px;"
                 [style.background]="ollamaStatus === 'online' ? '#e8f5e9' : '#fce4ec'"
                 [style.color]="ollamaStatus === 'online' ? 'var(--success)' : 'var(--danger)'">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">
                {{ ollamaStatus === 'online' ? 'check_circle' : 'error' }}
              </span>
              Ollama: {{ ollamaStatus === 'online' ? modelosOllama.length + ' modelo(s) disponível(is)' : 'Offline - aguarde o download dos modelos' }}
            </div>
          }

          <!-- llama.cpp SYCL -->
          @if (config.provider === 'llama-cpp') {
            <div class="form-group">
              <label>Modelo GGUF</label>
              @if (modelosLlamaCpp.length > 0) {
                <select class="form-control" [(ngModel)]="config.model_name" (ngModelChange)="onLlamaCppModelChange()">
                  @for (m of modelosLlamaCpp; track m.name) {
                    <option [value]="m.name">{{ m.name }} ({{ m.size_gb }} GB) {{ m.ativo ? '- ATIVO' : '' }}</option>
                  }
                </select>
              } @else {
                <input class="form-control" [(ngModel)]="config.model_name" placeholder="Nenhum modelo .gguf encontrado">
              }
            </div>

            <!-- Controle do servidor -->
            <div style="display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap;">
              @if (llamaServerRunning) {
                <button class="btn btn-outline" style="border-color: var(--danger); color: var(--danger); padding: 6px 14px; font-size: 13px;"
                        (click)="pararServidor()" [disabled]="servidorOperando">
                  <span class="material-icons" style="font-size: 16px;">stop</span>
                  {{ servidorOperando ? 'Aguarde...' : 'Desligar Servidor' }}
                </button>
                <button class="btn btn-outline" style="border-color: var(--primary); color: var(--primary); padding: 6px 14px; font-size: 13px;"
                        (click)="trocarModelo()" [disabled]="servidorOperando || !config.model_name">
                  <span class="material-icons" style="font-size: 16px;">swap_horiz</span>
                  {{ servidorOperando ? 'Trocando...' : 'Trocar Modelo e Reiniciar' }}
                </button>
              } @else {
                <button class="btn btn-primary" style="padding: 6px 14px; font-size: 13px;"
                        (click)="iniciarServidor()" [disabled]="servidorOperando">
                  <span class="material-icons" style="font-size: 16px;">play_arrow</span>
                  {{ servidorOperando ? 'Iniciando...' : 'Ligar Servidor' }}
                </button>
              }
            </div>

            <div style="padding: 8px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 12px;"
                 [style.background]="llamaServerRunning ? '#e8f5e9' : '#fce4ec'"
                 [style.color]="llamaServerRunning ? 'var(--success)' : 'var(--danger)'">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">
                {{ llamaServerRunning ? 'check_circle' : llamaCppStatus === 'checking' ? 'hourglass_empty' : 'power_settings_new' }}
              </span>
              @if (llamaServerRunning) {
                llama-server online (Intel Arc GPU) — Modelo: {{ llamaServerModelo || 'carregando...' }}
              } @else if (llamaCppStatus === 'checking') {
                Verificando llama-server...
              } @else {
                llama-server desligado — GPU livre para fine-tuning
              }
            </div>
            @if (servidorMsg) {
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">{{ servidorMsg }}</div>
            }

            <!-- GPU Info -->
            @if (gpuData?.disponivel) {
              <div style="padding: 10px 14px; background: var(--bg); border-radius: 8px; font-size: 13px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                  <span class="material-icons" style="font-size: 18px; color: var(--primary);">memory</span>
                  <strong>{{ gpuData.gpu_name }}</strong>
                </div>
                <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                  <span>VRAM Total: <strong>{{ gpuData.vram_total_gb }} GB</strong></span>
                  <span>Usada: <strong style="color: var(--danger);">{{ gpuData.vram_usada_gb }} GB</strong></span>
                  <span>Livre: <strong style="color: var(--success);">{{ gpuData.vram_livre_gb }} GB</strong></span>
                </div>
                <div style="margin-top: 6px; height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden;">
                  <div style="height: 100%; border-radius: 3px; transition: width 0.3s;"
                       [style.width.%]="(gpuData.vram_usada_gb / gpuData.vram_total_gb) * 100"
                       [style.background]="gpuData.vram_usada_gb / gpuData.vram_total_gb > 0.8 ? 'var(--danger)' : 'var(--primary)'">
                  </div>
                </div>
              </div>
            }
          }

          <!-- Fine-Tuned -->
          @if (config.provider === 'finetuned') {
            <div class="form-group">
              <label>Modelo Fine-Tuned</label>
              @if (modelosFinetuned.length > 0) {
                <select class="form-control" [(ngModel)]="config.model_name">
                  @for (m of modelosFinetuned; track m.name) {
                    <option [value]="m.name">{{ m.display_name }} — Loss: {{ m.loss_final || '?' }} ({{ m.dataset_size }} exemplos)</option>
                  }
                </select>
              } @else {
                <input class="form-control" [(ngModel)]="config.model_name" placeholder="Nenhum modelo fine-tuned" disabled>
              }
            </div>
            <div style="padding: 8px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 12px;"
                 [style.background]="finetunedStatus === 'online' ? '#e8f5e9' : '#fff3e0'"
                 [style.color]="finetunedStatus === 'online' ? 'var(--success)' : 'var(--warning)'">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">
                {{ finetunedStatus === 'online' ? 'check_circle' : finetunedStatus === 'checking' ? 'hourglass_empty' : 'info' }}
              </span>
              @if (finetunedStatus === 'online') {
                {{ modelosFinetuned.length }} modelo(s) fine-tuned disponível(is)
              } @else if (finetunedStatus === 'checking') {
                Verificando modelos fine-tuned...
              } @else {
                Nenhum modelo fine-tuned disponível. Treine um na seção Fine-Tuning.
              }
            </div>
          }

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label>Temperatura</label>
              <input class="form-control" type="number" [(ngModel)]="config.temperature" min="0" max="2" step="0.1">
            </div>
            <div class="form-group">
              <label>Max Tokens</label>
              <input class="form-control" type="number" [(ngModel)]="config.max_tokens" min="256" max="8192">
            </div>
          </div>
        </div>

        <!-- TTS/STT -->
        <div>
          <h3 style="font-size: 15px; margin-bottom: 12px; color: var(--primary);">Voz (TTS/STT)</h3>
          <div class="form-group">
            <label>Engine TTS (Texto para Voz)</label>
            <select class="form-control" [(ngModel)]="config.tts_engine">
              <option value="piper">Piper (Local, sem GPU)</option>
              <option value="browser">Web Speech API (Navegador)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Engine STT (Voz para Texto)</label>
            <select class="form-control" [(ngModel)]="config.stt_engine">
              <option value="vosk">Vosk (Local, sem GPU)</option>
              <option value="browser">Web Speech API (Navegador)</option>
            </select>
          </div>

          <div style="margin-top: 16px; padding: 12px; background: var(--bg); border-radius: 8px;">
            <strong style="font-size: 13px;">Modelos Locais (sem GPU):</strong>
            <ul style="font-size: 13px; margin-top: 8px; padding-left: 20px;">
              <li><strong>Piper TTS:</strong> pt_BR-faber-medium (ONNX)</li>
              <li><strong>Vosk STT:</strong> vosk-model-pt-br (pequeno)</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- RAG -->
      <div style="margin-top: 20px; border-top: 1px solid var(--border); padding-top: 20px;">
        <h3 style="font-size: 15px; margin-bottom: 12px; color: var(--primary);">
          <span class="material-icons" style="vertical-align: middle; font-size: 20px;">library_books</span>
          RAG - Base de Conhecimento
        </h3>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
          O RAG (Retrieval-Augmented Generation) enriquece as respostas da IA com dados reais do hospital:
          protocolos médicos, dados de scraping e prontuários.
        </p>

        <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
          <button class="btn btn-primary" (click)="indexarRAG()" [disabled]="indexandoRAG">
            <span class="material-icons">sync</span>
            {{ indexandoRAG ? 'Indexando...' : 'Reindexar Base' }}
          </button>
          @if (ragStats) {
            <div style="font-size: 13px; display: flex; gap: 16px;">
              <span><strong>{{ ragStats.total_documentos }}</strong> documentos indexados</span>
              @for (entry of ragTipos; track entry[0]) {
                <span style="color: var(--text-secondary);">{{ entry[0] }}: {{ entry[1] }}</span>
              }
            </div>
          }
        </div>
        @if (ragMensagem) {
          <span style="color: var(--success); font-size: 13px; display: block; margin-top: 8px;">{{ ragMensagem }}</span>
        }
      </div>

      <div style="margin-top: 20px; display: flex; gap: 8px;">
        <button class="btn btn-primary" (click)="salvar()" [disabled]="salvando">
          <span class="material-icons">save</span>
          {{ salvando ? 'Salvando...' : 'Salvar Configuração' }}
        </button>
        @if (mensagem) {
          <span style="color: var(--success); font-size: 14px; align-self: center;">{{ mensagem }}</span>
        }
      </div>
    </div>

    @if (configAtual) {
      <div class="card fade-in" style="margin-top: 16px;">
        <h3 style="font-size: 15px; margin-bottom: 12px;">Configuração Ativa</h3>
        <table class="table">
          <tr><td>Provider</td><td><strong>{{ configAtual.provider }}</strong></td></tr>
          <tr><td>Modelo</td><td><strong>{{ configAtual.model_name }}</strong></td></tr>
          <tr><td>Temperatura</td><td>{{ configAtual.temperature }}</td></tr>
          <tr><td>Max Tokens</td><td>{{ configAtual.max_tokens }}</td></tr>
          <tr><td>TTS</td><td>{{ configAtual.tts_engine }}</td></tr>
          <tr><td>STT</td><td>{{ configAtual.stt_engine }}</td></tr>
        </table>
      </div>
    }
  `,
})
export class ConfigComponent implements OnInit {
  config = {
    provider: 'llama-cpp',
    model_name: 'qwen3.5',
    base_url: 'http://llama-server:8080',
    temperature: 0.7,
    max_tokens: 2048,
    tts_engine: 'piper',
    stt_engine: 'vosk',
  };
  apiKey = '';
  configAtual?: ConfigLLM;
  salvando = false;
  mensagem = '';
  indexandoRAG = false;
  ragStats: any = null;
  ragTipos: [string, number][] = [];
  ragMensagem = '';
  modelosOllama: any[] = [];
  ollamaStatus = 'checking';
  modelosOpenAI: any[] = [];
  openaiStatus = 'checking';
  modelosLlamaCpp: any[] = [];
  llamaCppStatus = 'checking';
  llamaServerRunning = false;
  llamaServerModelo = '';
  servidorOperando = false;
  servidorMsg = '';
  gpuData: any = null;
  modelosFinetuned: any[] = [];
  finetunedStatus = 'checking';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.obterConfig().subscribe({
      next: (cfg) => {
        if (cfg) {
          this.configAtual = cfg;
          this.config = { ...this.config, ...cfg };
        }
        this.carregarModelos();
      },
    });
    this.carregarRAGStats();
  }

  onProviderChange(): void {
    if (this.config.provider === 'openai') {
      this.config.model_name = 'gpt-4o-mini';
      this.config.base_url = '';
    } else if (this.config.provider === 'llama-cpp') {
      this.config.model_name = 'qwen3.5-4b';
      this.config.base_url = 'http://host.docker.internal:8081';
    } else if (this.config.provider === 'finetuned') {
      this.config.model_name = '';
      this.config.base_url = '';
    } else {
      this.config.model_name = 'qwen3.5:4b';
      this.config.base_url = 'http://host.docker.internal:11434';
    }
    this.carregarModelos();
  }

  carregarModelos(): void {
    this.carregarModelosOllama();
    this.carregarModelosOpenAI();
    this.carregarModelosLlamaCpp();
    this.carregarModelosFinetuned();
    this.carregarGpuInfo();
  }

  carregarGpuInfo(): void {
    this.api.gpuInfo().subscribe({
      next: (data) => this.gpuData = data,
      error: () => this.gpuData = null,
    });
  }

  carregarModelosOllama(): void {
    this.api.listarModelosOllama().subscribe({
      next: (data) => {
        this.ollamaStatus = data.status;
        this.modelosOllama = data.modelos || [];
      },
      error: () => this.ollamaStatus = 'offline',
    });
  }

  carregarModelosOpenAI(): void {
    this.api.listarModelosOpenAI().subscribe({
      next: (data) => {
        this.openaiStatus = data.status;
        this.modelosOpenAI = data.modelos || [];
      },
      error: () => this.openaiStatus = 'erro',
    });
  }

  carregarModelosLlamaCpp(): void {
    this.llamaCppStatus = 'checking';
    this.api.listarModelosLlamaCpp().subscribe({
      next: (data) => {
        this.llamaCppStatus = data.status;
        this.modelosLlamaCpp = data.modelos || [];
        this.llamaServerRunning = data.status === 'online';
        this.llamaServerModelo = data.modelo_carregado || '';
        if (this.modelosLlamaCpp.length > 0 && !this.config.model_name) {
          // Seleciona o modelo ativo, ou o primeiro
          const ativo = this.modelosLlamaCpp.find((m: any) => m.ativo);
          this.config.model_name = ativo ? ativo.name : this.modelosLlamaCpp[0].name;
        }
      },
      error: () => { this.llamaCppStatus = 'offline'; this.llamaServerRunning = false; },
    });
  }

  onLlamaCppModelChange(): void {
    // Modelo único, base_url fixa
  }

  trocarModelo(): void {
    if (!this.config.model_name) return;
    this.servidorOperando = true;
    this.servidorMsg = 'Trocando modelo e reiniciando servidor...';
    this.api.trocarModelo(this.config.model_name).subscribe({
      next: (r) => {
        this.servidorMsg = r.msg || 'Modelo trocado!';
        this.llamaServerRunning = false;
        // Poll até servidor voltar
        this._pollServidorAteOnline();
      },
      error: (e) => {
        this.servidorOperando = false;
        this.servidorMsg = 'Erro ao trocar modelo: ' + (e.error?.erro || e.message);
      },
    });
  }

  pararServidor(): void {
    this.servidorOperando = true;
    this.servidorMsg = 'Desligando servidor...';
    this.api.pararLlamaServer().subscribe({
      next: () => {
        this.servidorOperando = false;
        this.llamaServerRunning = false;
        this.llamaCppStatus = 'offline';
        this.servidorMsg = 'Servidor desligado. GPU livre para fine-tuning.';
        this.carregarGpuInfo();
        setTimeout(() => this.servidorMsg = '', 5000);
      },
      error: () => {
        this.servidorOperando = false;
        this.servidorMsg = 'Erro ao desligar servidor';
      },
    });
  }

  iniciarServidor(): void {
    this.servidorOperando = true;
    this.servidorMsg = 'Iniciando servidor...';
    this.api.iniciarLlamaServer().subscribe({
      next: () => {
        this.servidorMsg = 'Servidor iniciando, aguarde o carregamento do modelo...';
        this._pollServidorAteOnline();
      },
      error: () => {
        this.servidorOperando = false;
        this.servidorMsg = 'Erro ao iniciar servidor';
      },
    });
  }

  private _pollServidorAteOnline(): void {
    let tentativas = 0;
    const poll = setInterval(() => {
      tentativas++;
      this.api.listarModelosLlamaCpp().subscribe({
        next: (data) => {
          if (data.status === 'online') {
            clearInterval(poll);
            this.servidorOperando = false;
            this.llamaServerRunning = true;
            this.llamaCppStatus = 'online';
            this.llamaServerModelo = data.modelo_carregado || '';
            this.modelosLlamaCpp = data.modelos || [];
            this.servidorMsg = 'Servidor online!';
            this.carregarGpuInfo();
            setTimeout(() => this.servidorMsg = '', 3000);
          } else if (tentativas > 40) {
            clearInterval(poll);
            this.servidorOperando = false;
            this.servidorMsg = 'Timeout aguardando servidor. Verifique os logs.';
          }
        },
      });
    }, 5000);
  }

  carregarModelosFinetuned(): void {
    this.finetunedStatus = 'checking';
    this.api.listarModelosFinetuned().subscribe({
      next: (data) => {
        this.finetunedStatus = data.status;
        this.modelosFinetuned = data.modelos || [];
        if (this.config.provider === 'finetuned' && this.modelosFinetuned.length > 0 && !this.config.model_name) {
          this.config.model_name = this.modelosFinetuned[0].name;
        }
      },
      error: () => this.finetunedStatus = 'vazio',
    });
  }

  carregarRAGStats(): void {
    this.api.ragStats().subscribe({
      next: (stats) => {
        this.ragStats = stats;
        this.ragTipos = Object.entries(stats.por_tipo || {}) as [string, number][];
      },
    });
  }

  indexarRAG(): void {
    this.indexandoRAG = true;
    this.ragMensagem = '';
    this.api.indexarRAG().subscribe({
      next: (r) => {
        this.indexandoRAG = false;
        this.ragMensagem = `Indexação concluída: ${r.total_documentos} documentos.`;
        this.carregarRAGStats();
        setTimeout(() => this.ragMensagem = '', 5000);
      },
      error: () => {
        this.indexandoRAG = false;
        this.ragMensagem = 'Erro na indexação.';
      },
    });
  }

  salvar(): void {
    this.salvando = true;
    this.mensagem = '';
    const dados: any = { ...this.config };
    if (this.apiKey) dados.api_key = this.apiKey;

    this.api.salvarConfig(dados).subscribe({
      next: (cfg) => {
        this.configAtual = cfg;
        this.mensagem = 'Configuração salva com sucesso!';
        this.salvando = false;
        this.carregarModelos();
        setTimeout(() => this.mensagem = '', 3000);
      },
      error: () => { this.mensagem = 'Erro ao salvar'; this.salvando = false; },
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1e9) return (bytes / 1e6).toFixed(0) + ' MB';
    return (bytes / 1e9).toFixed(1) + ' GB';
  }
}
