import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ModeloFineTuning, FineTuningJob, DatasetEntry } from '../../models/models';

@Component({
  selector: 'app-finetuning',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 4px;">
        <span class="material-icons" style="vertical-align: middle;">model_training</span>
        Fine-Tuning de LLM
      </h2>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        Personalize modelos de linguagem com dados médicos usando PEFT/LoRA
      </p>

      <!-- Tabs -->
      <div style="display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 20px;">
        @for (tab of tabs; track tab.id) {
          <button class="tab-btn" [class.tab-active]="abaAtiva === tab.id" (click)="abaAtiva = tab.id">
            <span class="material-icons" style="font-size: 18px;">{{ tab.icone }}</span>
            {{ tab.label }}
          </button>
        }
      </div>

      <!-- Tab: Treinar -->
      @if (abaAtiva === 'treinar') {
        <div class="fade-in">
          <!-- Modelo -->
          <h3 class="section-title">
            <span class="material-icons">psychology</span>
            Selecionar Modelo Base
          </h3>
          <div class="model-grid">
            @for (m of modelos; track m.id) {
              <div class="model-card" [class.model-selected]="config.modelo_base === m.id"
                   (click)="config.modelo_base = m.id">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                  <strong style="font-size: 14px;">{{ m.nome }}</strong>
                  <span class="param-badge">{{ m.parametros }}</span>
                </div>
                <p style="font-size: 12px; color: var(--text-secondary); margin: 6px 0;">{{ m.descricao }}</p>
                <div style="font-size: 11px; color: var(--text-secondary); display: flex; flex-wrap: wrap; gap: 8px;">
                  <span>Inferência: {{ m.ram_estimada }}</span>
                  @if (m.vram_treino) {
                    <span>Treino: {{ m.vram_treino }}</span>
                  }
                </div>
                @if (m.dispositivo) {
                  <div style="font-size: 11px; margin-top: 4px; padding: 2px 8px; background: var(--bg); border-radius: 8px; display: inline-block;"
                       [style.color]="m.dispositivo.includes('GPU') ? 'var(--success)' : 'var(--warning)'">
                    {{ m.dispositivo }}
                  </div>
                }
              </div>
            }
          </div>

          <!-- Hiperparâmetros -->
          <h3 class="section-title" style="margin-top: 20px;">
            <span class="material-icons">tune</span>
            Hiperparâmetros
          </h3>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
            <div class="form-group">
              <label>Épocas
                <span class="info-tip" data-tip="Quantas vezes o modelo percorre todo o dataset. Mais épocas = mais aprendizado, mas pode causar overfitting. Convencional: 1-5 para fine-tuning LoRA.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.epocas" min="1" max="20">
            </div>
            <div class="form-group">
              <label>Learning Rate
                <span class="info-tip" data-tip="Velocidade de aprendizado. Valores menores = aprendizado mais estável e lento. Valores maiores = mais rápido mas instável. Convencional: 1e-4 a 3e-4 para LoRA.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.learning_rate" min="0.00001" max="0.01" step="0.0001">
            </div>
            <div class="form-group">
              <label>LoRA Rank (r)
                <span class="info-tip" data-tip="Dimensão das matrizes de adaptação LoRA. Maior rank = mais capacidade de aprendizado, mas mais memória. Convencional: 8-16 para modelos pequenos, 32-64 para maior qualidade.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.lora_r" min="2" max="64">
            </div>
            <div class="form-group">
              <label>LoRA Alpha
                <span class="info-tip" data-tip="Fator de escala do LoRA. Controla a intensidade da adaptação. Regra geral: alpha = 2x o rank. Convencional: 16-32. Maior alpha = adaptação mais forte.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.lora_alpha" min="4" max="128">
            </div>
            <div class="form-group">
              <label>Batch Size
                <span class="info-tip" data-tip="Exemplos processados por step de treino. Maior batch = treino mais estável e rápido, mas exige mais memória. Convencional: 1-4 para GPU com 16GB, 2-8 para maior VRAM.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.batch_size" min="1" max="16">
            </div>
            <div class="form-group">
              <label>Max Length
                <span class="info-tip" data-tip="Tamanho máximo (em tokens) de cada exemplo do dataset. Textos maiores que isso são truncados. Convencional: 256-512 para Q&A curto, 1024-2048 para textos longos.">i</span>
              </label>
              <input class="form-control" type="number" [(ngModel)]="config.max_length" min="128" max="2048" step="128">
            </div>
          </div>

          <!-- Info dataset -->
          <div class="info-box" style="margin-top: 16px;">
            <span class="material-icons" style="font-size: 18px; color: var(--primary);">dataset</span>
            <span>Dataset: <strong>{{ datasetStats?.total || 0 }}</strong> exemplos ativos</span>
            @if (datasetStats?.total === 0) {
              <span style="color: var(--warning);"> — Importe ou adicione dados na aba Dataset</span>
            }
          </div>

          <!-- Botão iniciar -->
          <div style="margin-top: 20px;">
            <button class="btn btn-primary" (click)="iniciarTreinamento()"
                    [disabled]="treinando || !datasetStats?.total">
              <span class="material-icons">play_arrow</span>
              {{ treinando ? 'Treinamento em andamento...' : 'Iniciar Fine-Tuning' }}
            </button>
          </div>
        </div>
      }

      <!-- Tab: Progresso -->
      @if (abaAtiva === 'progresso') {
        <div class="fade-in">
          @if (jobAtivo) {
            <div class="progress-card">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>
                  <strong>{{ jobAtivo.modelo_base }}</strong>
                  <span class="status-badge" [class]="'status-' + jobAtivo.status">{{ statusLabel(jobAtivo.status) }}</span>
                </div>
                @if (jobAtivo.status === 'treinando') {
                  <button class="btn btn-danger" style="padding: 6px 14px; font-size: 13px;" (click)="cancelarTreinamento()">
                    <span class="material-icons" style="font-size: 16px;">stop</span>
                    Cancelar
                  </button>
                }
              </div>

              <!-- Barra de progresso -->
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" [style.width.%]="jobAtivo.progresso"
                     [class.progress-done]="jobAtivo.status === 'concluido'"
                     [class.progress-error]="jobAtivo.status === 'erro'">
                </div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                <span>{{ jobAtivo.progresso }}%</span>
                <span>Época {{ jobAtivo.epoca_atual }} / {{ jobAtivo.epocas_total }}</span>
                @if (jobAtivo.loss_atual) {
                  <span>Loss: {{ jobAtivo.loss_atual }}</span>
                }
              </div>

              <!-- Métricas -->
              <div class="metrics-grid">
                <div class="metric-item">
                  <span class="metric-label">Dataset</span>
                  <span class="metric-value">{{ jobAtivo.dataset_size }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">Learning Rate</span>
                  <span class="metric-value">{{ jobAtivo.learning_rate }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">LoRA r/α</span>
                  <span class="metric-value">{{ jobAtivo.lora_r }}/{{ jobAtivo.lora_alpha }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">Batch Size</span>
                  <span class="metric-value">{{ jobAtivo.batch_size }}</span>
                </div>
              </div>

              @if (jobAtivo.erro_msg) {
                <div style="margin-top: 12px; padding: 10px; background: #fde8e8; border-radius: 8px; color: var(--danger); font-size: 13px;">
                  <strong>Erro:</strong> {{ jobAtivo.erro_msg }}
                </div>
              }

              @if (jobAtivo.caminho_modelo) {
                <div style="margin-top: 12px; padding: 10px; background: #e8f5e9; border-radius: 8px; color: var(--success); font-size: 13px;">
                  <strong>Modelo salvo:</strong> {{ jobAtivo.caminho_modelo }}
                </div>
              }

              <!-- Logs -->
              @if (jobAtivo.logs) {
                <details style="margin-top: 12px;">
                  <summary style="cursor: pointer; font-size: 13px; font-weight: 500; color: var(--text-secondary);">
                    <span class="material-icons" style="font-size: 16px; vertical-align: middle;">terminal</span>
                    Logs de Treinamento
                  </summary>
                  <pre class="log-box">{{ jobAtivo.logs }}</pre>
                </details>
              }
            </div>
          } @else {
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
              <span class="material-icons" style="font-size: 48px; opacity: 0.4;">hourglass_empty</span>
              <p style="margin-top: 8px;">Nenhum treinamento ativo. Inicie um na aba Treinar.</p>
            </div>
          }

          <!-- Histórico -->
          @if (jobs.length > 1 || (jobs.length === 1 && !jobAtivo)) {
            <h3 class="section-title" style="margin-top: 24px;">
              <span class="material-icons">history</span>
              Histórico
            </h3>
            <table class="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Modelo</th>
                  <th>Status</th>
                  <th>Progresso</th>
                  <th>Loss</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                @for (j of jobs; track j.id) {
                  <tr style="cursor: pointer;" (click)="jobAtivo = j">
                    <td>{{ j.id }}</td>
                    <td>{{ j.modelo_base.split('/').pop() }}</td>
                    <td><span class="status-badge" [class]="'status-' + j.status">{{ statusLabel(j.status) }}</span></td>
                    <td>{{ j.progresso }}%</td>
                    <td>{{ j.loss_atual || '-' }}</td>
                    <td>{{ j.criado_em | date:'dd/MM HH:mm' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      }

      <!-- Tab: Dataset -->
      @if (abaAtiva === 'dataset') {
        <div class="fade-in">
          <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
            <button class="btn btn-primary" (click)="mostrarFormDataset = !mostrarFormDataset">
              <span class="material-icons">add</span>
              Adicionar Exemplo
            </button>
            <button class="btn btn-outline" (click)="importarJSON()" [disabled]="importando">
              <span class="material-icons">upload_file</span>
              {{ importando ? 'Importando...' : 'Importar JSON' }}
            </button>
            <div style="flex: 1;"></div>
            <div style="position: relative;">
              <input class="form-control" [(ngModel)]="filtroDataset" placeholder="Buscar no dataset..."
                     style="font-size: 12px; padding-left: 30px; width: 220px;">
              <span class="material-icons" style="position: absolute; left: 8px; top: 50%; transform: translateY(-50%); font-size: 16px; color: var(--text-secondary);">search</span>
            </div>
            <span style="font-size: 13px; align-self: center; color: var(--text-secondary);">
              {{ datasetFiltrado.length }}/{{ dataset.length }}
            </span>
          </div>

          <!-- Gerar dataset automaticamente -->
          <div style="display: flex; gap: 8px; margin-bottom: 16px; align-items: end; flex-wrap: wrap;">
            <div class="form-group" style="margin-bottom: 0; flex: 1; min-width: 200px;">
              <label>Gerar dataset sobre doença</label>
              <input class="form-control" [(ngModel)]="doencaGerar" placeholder="Ex: diabetes, pneumonia, hipertensão...">
            </div>
            <button class="btn btn-outline" (click)="gerarDataset()" [disabled]="!doencaGerar || gerando"
                    style="border-color: var(--primary); color: var(--primary); white-space: nowrap;">
              <span class="material-icons">auto_awesome</span>
              {{ gerando ? 'Gerando...' : 'Gerar Automaticamente' }}
            </button>
          </div>

          @if (mensagemGerar) {
            <div style="margin-bottom: 16px; padding: 10px 16px; background: #e8f5e9; border-radius: 8px; color: var(--success); font-size: 13px;">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">check_circle</span>
              {{ mensagemGerar }}
            </div>
          }

          @if (erroGerar) {
            <div style="margin-bottom: 16px; padding: 10px 16px; background: #fce4ec; border-radius: 8px; color: var(--danger); font-size: 13px;">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">error</span>
              {{ erroGerar }}
            </div>
          }

          <!-- Form adicionar -->
          @if (mostrarFormDataset) {
            <div class="card fade-in" style="border: 2px solid var(--primary); margin-bottom: 16px;">
              <h4 style="font-size: 14px; margin-bottom: 12px;">Novo Exemplo de Treinamento</h4>
              <div class="form-group">
                <label>Pergunta / Instrução *</label>
                <textarea class="form-control" [(ngModel)]="novaEntrada.pergunta" rows="2"
                          placeholder="Ex: Quais são os sintomas de pneumonia?"></textarea>
              </div>
              <div class="form-group">
                <label>Contexto (opcional)</label>
                <input class="form-control" [(ngModel)]="novaEntrada.contexto"
                       placeholder="Ex: Protocolo de emergência respiratória">
              </div>
              <div class="form-group">
                <label>Resposta Esperada *</label>
                <textarea class="form-control" [(ngModel)]="novaEntrada.resposta" rows="3"
                          placeholder="Ex: Os principais sintomas incluem..."></textarea>
              </div>
              <div class="form-group">
                <label>Categoria</label>
                <input class="form-control" [(ngModel)]="novaEntrada.categoria"
                       placeholder="Ex: protocolo_medico, triagem, medicamento">
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" (click)="adicionarEntrada()"
                        [disabled]="!novaEntrada.pergunta || !novaEntrada.resposta">
                  <span class="material-icons">save</span> Salvar
                </button>
                <button class="btn btn-outline" (click)="mostrarFormDataset = false">Cancelar</button>
              </div>
            </div>
          }

          <!-- Tabela dataset -->
          @if (dataset.length) {
            <div style="overflow-x: auto;">
              <table class="table">
                <thead>
                  <tr>
                    <th style="width: 30%;">Pergunta</th>
                    <th style="width: 15%;">Contexto</th>
                    <th style="width: 35%;">Resposta</th>
                    <th>Categoria</th>
                    <th style="width: 40px;"></th>
                  </tr>
                </thead>
                <tbody>
                  @for (e of datasetFiltrado; track e.id) {
                    @if (e.ativo) {
                      <tr>
                        <td style="font-size: 13px;">{{ truncar(e.pergunta, 80) }}</td>
                        <td style="font-size: 12px; color: var(--text-secondary);">{{ truncar(e.contexto || '-', 40) }}</td>
                        <td style="font-size: 13px;">{{ truncar(e.resposta, 100) }}</td>
                        <td>
                          @if (e.categoria) {
                            <span class="cat-badge">{{ e.categoria }}</span>
                          }
                        </td>
                        <td>
                          <button class="btn-icon" (click)="removerEntrada(e.id)" title="Remover">
                            <span class="material-icons" style="font-size: 18px; color: var(--danger);">delete</span>
                          </button>
                        </td>
                      </tr>
                    }
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
              <span class="material-icons" style="font-size: 48px; opacity: 0.4;">folder_open</span>
              <p style="margin-top: 8px;">Dataset vazio. Adicione exemplos ou importe do JSON.</p>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .tab-btn {
      display: flex; align-items: center; gap: 6px;
      padding: 10px 20px; border: none; background: none;
      font-size: 14px; cursor: pointer; color: var(--text-secondary);
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-active { color: var(--primary) !important; border-bottom-color: var(--primary) !important; font-weight: 500; }

    .section-title {
      font-size: 15px; margin-bottom: 12px; color: var(--text);
      display: flex; align-items: center; gap: 6px;
    }
    .section-title .material-icons { font-size: 20px; color: var(--primary); }

    .model-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px;
    }
    .model-card {
      padding: 14px; border: 2px solid var(--border); border-radius: 10px;
      cursor: pointer; transition: all 0.2s;
    }
    .model-card:hover { border-color: var(--primary); background: rgba(26,115,232,0.03); }
    .model-selected { border-color: var(--primary) !important; background: rgba(26,115,232,0.06) !important; }

    .param-badge {
      font-size: 11px; font-weight: 600; padding: 2px 8px;
      background: var(--bg); border-radius: 12px; color: var(--primary);
    }

    .info-tip {
      display: inline-flex; align-items: center; justify-content: center;
      width: 16px; height: 16px; border-radius: 50%;
      background: var(--primary); color: #fff;
      font-size: 10px; font-weight: 700; font-style: italic;
      cursor: help; margin-left: 4px; vertical-align: middle;
      position: relative; user-select: none; flex-shrink: 0;
    }
    .info-tip::after {
      content: attr(data-tip);
      position: absolute; bottom: calc(100% + 8px); left: 50%;
      transform: translateX(-50%);
      background: #1e1e1e; color: #f0f0f0;
      padding: 10px 14px; border-radius: 8px;
      font-size: 12px; font-weight: 400; font-style: normal;
      line-height: 1.5; white-space: normal;
      width: 280px; max-width: 90vw;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      opacity: 0; visibility: hidden;
      transition: opacity 0.2s, visibility 0.2s;
      pointer-events: none; z-index: 100;
    }
    .info-tip::before {
      content: '';
      position: absolute; bottom: calc(100% + 2px); left: 50%;
      transform: translateX(-50%);
      border: 6px solid transparent; border-top-color: #1e1e1e;
      opacity: 0; visibility: hidden;
      transition: opacity 0.2s, visibility 0.2s;
      pointer-events: none; z-index: 100;
    }
    .info-tip:hover::after,
    .info-tip:hover::before {
      opacity: 1; visibility: visible;
    }

    .info-box {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px; background: var(--bg); border-radius: 8px; font-size: 13px;
    }

    .progress-card { padding: 0; }
    .progress-bar-bg {
      height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%; background: var(--primary); border-radius: 4px;
      transition: width 0.5s ease;
    }
    .progress-done { background: var(--success) !important; }
    .progress-error { background: var(--danger) !important; }

    .metrics-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px; margin-top: 16px;
    }
    .metric-item {
      padding: 10px; background: var(--bg); border-radius: 8px; text-align: center;
    }
    .metric-label { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; }
    .metric-value { font-size: 16px; font-weight: 600; color: var(--text); }

    .status-badge {
      display: inline-block; padding: 2px 10px; border-radius: 12px;
      font-size: 12px; font-weight: 500; margin-left: 8px;
    }
    .status-pendente { background: var(--bg); color: var(--text-secondary); }
    .status-treinando { background: #e3f2fd; color: var(--primary); }
    .status-concluido { background: #e8f5e9; color: var(--success); }
    .status-erro { background: #fde8e8; color: var(--danger); }

    .log-box {
      margin-top: 8px; padding: 12px; background: #1e1e1e; color: #d4d4d4;
      border-radius: 8px; font-size: 12px; font-family: 'Fira Code', monospace;
      max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;
    }

    .cat-badge {
      font-size: 11px; padding: 2px 8px; background: var(--bg);
      border-radius: 10px; color: var(--text-secondary);
    }
  `],
})
export class FinetuningComponent implements OnInit, OnDestroy {
  tabs = [
    { id: 'treinar', label: 'Treinar', icone: 'play_circle' },
    { id: 'progresso', label: 'Progresso', icone: 'trending_up' },
    { id: 'dataset', label: 'Dataset', icone: 'storage' },
  ];
  abaAtiva = 'treinar';

  modelos: ModeloFineTuning[] = [];
  jobs: FineTuningJob[] = [];
  jobAtivo?: FineTuningJob;
  dataset: DatasetEntry[] = [];
  datasetStats: any = null;
  treinando = false;
  importando = false;
  mostrarFormDataset = false;
  filtroDataset = '';
  pollInterval?: any;

  config = {
    modelo_base: 'Qwen/Qwen3.5-4B',
    epocas: 3,
    learning_rate: 0.0002,
    lora_r: 8,
    lora_alpha: 16,
    batch_size: 2,
    max_length: 512,
  };

  novaEntrada = { pergunta: '', contexto: '', resposta: '', categoria: '' };
  doencaGerar = '';
  gerando = false;
  mensagemGerar = '';
  erroGerar = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listarModelosFT().subscribe(m => this.modelos = m);
    this.api.datasetStats().subscribe(s => this.datasetStats = s);
    this.carregarJobs();
    this.carregarDataset();
    this.iniciarPolling();
  }

  ngOnDestroy(): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  get datasetFiltrado(): DatasetEntry[] {
    if (!this.filtroDataset.trim()) return this.dataset.filter(e => e.ativo);
    const f = this.filtroDataset.toLowerCase();
    return this.dataset.filter(e => e.ativo && (
      e.pergunta.toLowerCase().includes(f) ||
      e.resposta.toLowerCase().includes(f) ||
      (e.categoria || '').toLowerCase().includes(f) ||
      (e.contexto || '').toLowerCase().includes(f)
    ));
  }

  carregarJobs(): void {
    this.api.listarJobs().subscribe(jobs => {
      this.jobs = jobs;
      const ativo = jobs.find(j => j.status === 'treinando' || j.status === 'pendente');
      if (ativo) {
        this.jobAtivo = ativo;
        this.treinando = true;
      } else if (jobs.length && !this.jobAtivo) {
        this.jobAtivo = jobs[0];
        this.treinando = false;
      } else if (this.jobAtivo) {
        const atualizado = jobs.find(j => j.id === this.jobAtivo!.id);
        if (atualizado) {
          this.jobAtivo = atualizado;
          if (atualizado.status !== 'treinando' && atualizado.status !== 'pendente') {
            this.treinando = false;
          }
        }
      }
    });
  }

  carregarDataset(): void {
    this.api.listarDataset().subscribe(d => this.dataset = d);
  }

  iniciarPolling(): void {
    this.pollInterval = setInterval(() => {
      if (this.treinando && this.jobAtivo) {
        this.api.obterJob(this.jobAtivo.id).subscribe(j => {
          this.jobAtivo = j;
          const idx = this.jobs.findIndex(x => x.id === j.id);
          if (idx >= 0) this.jobs[idx] = j;
          if (j.status !== 'treinando' && j.status !== 'pendente') {
            this.treinando = false;
          }
        });
      }
    }, 2000);
  }

  iniciarTreinamento(): void {
    this.treinando = true;
    this.api.iniciarFineTuning(this.config).subscribe({
      next: (job) => {
        this.jobAtivo = job;
        this.jobs.unshift(job);
        this.abaAtiva = 'progresso';
      },
      error: (err) => {
        this.treinando = false;
        alert(err.error?.detail || 'Erro ao iniciar treinamento');
      },
    });
  }

  cancelarTreinamento(): void {
    if (!this.jobAtivo) return;
    this.api.cancelarJob(this.jobAtivo.id).subscribe(() => {
      this.treinando = false;
      this.carregarJobs();
    });
  }

  adicionarEntrada(): void {
    this.api.adicionarDatasetEntry(this.novaEntrada).subscribe(e => {
      this.dataset.unshift(e);
      this.novaEntrada = { pergunta: '', contexto: '', resposta: '', categoria: '' };
      this.mostrarFormDataset = false;
      this.api.datasetStats().subscribe(s => this.datasetStats = s);
    });
  }

  removerEntrada(id: number): void {
    this.api.removerDatasetEntry(id).subscribe(() => {
      const entry = this.dataset.find(e => e.id === id);
      if (entry) entry.ativo = false;
      this.api.datasetStats().subscribe(s => this.datasetStats = s);
    });
  }

  gerarDataset(): void {
    this.gerando = true;
    this.mensagemGerar = '';
    this.erroGerar = '';
    this.api.gerarDatasetDoenca(this.doencaGerar).subscribe({
      next: (r) => {
        this.gerando = false;
        this.mensagemGerar = `${r.gerados} entradas geradas para "${r.doenca}" com sucesso!`;
        this.doencaGerar = '';
        this.carregarDataset();
        this.api.datasetStats().subscribe(s => this.datasetStats = s);
      },
      error: (err) => {
        this.gerando = false;
        this.erroGerar = err.error?.detail || 'Erro ao gerar dataset automaticamente.';
      },
    });
  }

  importarJSON(): void {
    this.importando = true;
    this.api.importarDatasetJSON().subscribe({
      next: (r) => {
        this.importando = false;
        this.carregarDataset();
        this.api.datasetStats().subscribe(s => this.datasetStats = s);
      },
      error: () => this.importando = false,
    });
  }

  truncar(texto: string, max: number): string {
    return texto.length > max ? texto.substring(0, max) + '...' : texto;
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      pendente: 'Pendente',
      treinando: 'Treinando',
      concluido: 'Concluído',
      erro: 'Erro',
    };
    return labels[status] || status;
  }
}
