import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { DadoMedico } from '../../models/models';

@Component({
  selector: 'app-scraping',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 4px;">
        <span class="material-icons" style="vertical-align: middle; color: var(--primary);">travel_explore</span>
        Scraping Inteligente de Dados Medicos
      </h2>
      <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">
        Agente com IA que pesquisa, navega, extrai e gera dataset automaticamente
      </p>

      <!-- Agente Inteligente -->
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <input class="form-control" [(ngModel)]="tema" placeholder="Digite um tema medico... Ex: diabetes, pneumonia, sepse"
               (keyup.enter)="executarAgente()" style="flex: 1; font-size: 14px;">
        <button class="btn btn-primary" (click)="executarAgente()" [disabled]="!tema || carregandoAgente"
                style="white-space: nowrap; padding: 8px 20px;">
          <span class="material-icons">{{ carregandoAgente ? 'hourglass_top' : 'rocket_launch' }}</span>
          {{ carregandoAgente ? 'Agente trabalhando...' : 'Pesquisar com IA' }}
        </button>
      </div>

      <!-- Progresso do agente -->
      @if (carregandoAgente) {
        <div class="agente-progresso">
          <div class="progresso-header">
            <span class="material-icons spin">psychology</span>
            <span>Agente pesquisando sobre <strong>{{ tema }}</strong>...</span>
          </div>
          <div class="passos-list">
            @for (msg of progressoMensagens; track msg) {
              <div class="passo-item fade-in">
                <span class="material-icons" style="font-size: 14px; color: var(--success);">check_circle</span>
                {{ msg }}
              </div>
            }
            <div class="passo-item fade-in" style="color: var(--primary);">
              <span class="material-icons spin" style="font-size: 14px;">sync</span>
              {{ passoAtual }}
            </div>
          </div>
        </div>
      }

      <!-- Resultado do agente -->
      @if (resultadoAgente) {
        <div class="agente-resultado fade-in">
          <div class="resultado-header">
            <span class="material-icons" style="color: var(--success);">task_alt</span>
            <div>
              <strong>Pesquisa concluida: {{ resultadoAgente.tema }}</strong>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                {{ resultadoAgente.total_dados }} dados coletados | {{ resultadoAgente.total_dataset }} entradas no dataset
              </div>
            </div>
          </div>
          <!-- Perguntas planejadas -->
          @if (resultadoAgente.perguntas_planejadas?.length) {
            <details style="margin-bottom: 8px;">
              <summary class="detalhe-toggle">
                <span class="material-icons" style="font-size: 14px;">psychology</span>
                Perguntas planejadas pela IA ({{ resultadoAgente.perguntas_planejadas.length }})
              </summary>
              <div class="detalhe-conteudo">
                @for (p of resultadoAgente.perguntas_planejadas; track p) {
                  <div class="detalhe-item">{{ p }}</div>
                }
              </div>
            </details>
          }

          <div class="passos-list">
            @for (p of resultadoAgente.passos; track p.passo) {
              <details class="passo-resultado">
                <summary style="cursor: pointer; display: flex; align-items: center; gap: 6px;">
                  <span class="material-icons" style="font-size: 16px; color: var(--success);">check_circle</span>
                  <strong style="font-size: 13px; flex: 1;">{{ p.acao }}</strong>
                  <span class="passo-fonte">{{ p.fonte }}</span>
                  <span style="font-size: 11px; color: var(--text-secondary);">
                    {{ p.resultado }}
                    @if (p.dataset_gerado > 0) {
                      | <span style="color: var(--primary);">+{{ p.dataset_gerado }} dataset</span>
                    }
                  </span>
                  @if (p.itens?.length || p.qa_gerados?.length) {
                    <span class="material-icons" style="font-size: 16px; color: var(--text-secondary);">expand_more</span>
                  }
                </summary>

                <!-- Itens coletados -->
                @if (p.itens?.length) {
                  <div class="detalhe-conteudo">
                    @for (item of p.itens; track item.titulo) {
                      <div class="dado-item">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                          <strong style="font-size: 12px;">{{ item.titulo }}</strong>
                          @if (item.url) {
                            <a [href]="item.url" target="_blank" style="color: var(--primary); flex-shrink: 0;">
                              <span class="material-icons" style="font-size: 14px;">open_in_new</span>
                            </a>
                          }
                        </div>
                        <p style="font-size: 11px; color: var(--text-secondary); margin: 4px 0 0;">
                          {{ item.conteudo_preview }}...
                        </p>
                        <span class="passo-fonte" style="font-size: 9px;">{{ item.fonte }}</span>
                      </div>
                    }
                  </div>
                }

                <!-- Q&A gerados -->
                @if (p.qa_gerados?.length) {
                  <div class="detalhe-conteudo">
                    @for (qa of p.qa_gerados; track qa.pergunta) {
                      <div class="qa-item">
                        <div style="font-size: 12px; font-weight: 600; color: var(--primary);">
                          <span class="material-icons" style="font-size: 12px; vertical-align: middle;">help</span>
                          {{ qa.pergunta }}
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; padding-left: 16px;">
                          {{ qa.resposta_preview }}...
                        </div>
                        <span class="passo-fonte" style="font-size: 9px; margin-left: 16px;">{{ qa.fonte }}</span>
                      </div>
                    }
                  </div>
                }
              </details>
            }
          </div>
        </div>
      }

      @if (erro) {
        <div style="padding: 10px 16px; background: #fce4ec; border-radius: 8px; color: var(--danger); font-size: 13px; margin-top: 12px;">
          <span class="material-icons" style="font-size: 16px; vertical-align: middle;">error</span>
          {{ erro }}
        </div>
      }
    </div>

    <!-- Busca manual -->
    <div class="card" style="margin-top: 12px;">
      <details>
        <summary style="cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text-secondary);">
          <span class="material-icons" style="font-size: 16px; vertical-align: middle;">tune</span>
          Busca Manual por Fonte
        </summary>
        <div style="margin-top: 12px;">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-bottom: 12px;">
            <div class="form-group">
              <label>Fonte</label>
              <select class="form-control" [(ngModel)]="fonte">
                @for (f of fontes; track f.value) {
                  <option [value]="f.value">{{ f.label }}</option>
                }
              </select>
            </div>
            <div class="form-group">
              <label>Termo</label>
              <input class="form-control" [(ngModel)]="termoManual" placeholder="Buscar...">
            </div>
            <div class="form-group">
              <label>Max</label>
              <input class="form-control" type="number" [(ngModel)]="maxResultados" min="1" max="50">
            </div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn btn-outline" (click)="buscarManual()" [disabled]="!termoManual || carregando" style="font-size: 13px;">
              <span class="material-icons">search</span> Buscar
            </button>
            <button class="btn btn-outline" (click)="buscarTodas()" [disabled]="!termoManual || carregandoTodas" style="font-size: 13px;">
              <span class="material-icons">travel_explore</span> Todas as Fontes
            </button>
          </div>
        </div>
      </details>
    </div>

    <!-- URL Livre -->
    <div class="card" style="margin-top: 12px;">
      <details>
        <summary style="cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text-secondary);">
          <span class="material-icons" style="font-size: 16px; vertical-align: middle;">link</span>
          Scraping por URL
        </summary>
        <div style="margin-top: 12px; display: flex; gap: 8px;">
          <input class="form-control" [(ngModel)]="urlLivre" placeholder="https://exemplo.com/artigo-medico" style="flex: 1;">
          <button class="btn btn-outline" (click)="scrapingUrl()" [disabled]="!urlLivre || carregandoUrl" style="font-size: 13px;">
            <span class="material-icons">download</span> {{ carregandoUrl ? 'Coletando...' : 'Coletar' }}
          </button>
        </div>
        @if (resultadoUrl) {
          <div style="margin-top: 8px; padding: 8px 12px; background: #e8f5e9; border-radius: 8px; font-size: 12px; color: var(--success);">
            <span class="material-icons" style="font-size: 14px; vertical-align: middle;">check_circle</span>
            <strong>{{ resultadoUrl.titulo }}</strong> — {{ resultadoUrl.dataset_entradas_criadas }} entradas geradas
          </div>
        }
      </details>
    </div>

    <!-- Resultados manuais -->
    @if (dados.length > 0) {
      <div class="card fade-in" style="margin-top: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="font-size: 15px;">Resultados ({{ dados.length }})</h3>
          <button class="btn btn-primary" (click)="enviarParaDataset()" [disabled]="enviandoDataset" style="font-size: 12px; padding: 4px 12px;">
            <span class="material-icons" style="font-size: 14px;">model_training</span>
            {{ enviandoDataset ? 'Enviando...' : 'Enviar para Dataset' }}
          </button>
        </div>
        @if (mensagemDataset) {
          <div style="margin-bottom: 8px; padding: 6px 12px; background: #e8f5e9; border-radius: 8px; font-size: 12px; color: var(--success);">{{ mensagemDataset }}</div>
        }
        @for (d of dados; track d.id) {
          <div style="padding: 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 6px; font-size: 13px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
              <div>
                <strong>{{ d.titulo }}</strong>
                <span class="passo-fonte" style="margin-left: 6px;">{{ d.fonte }}</span>
              </div>
              @if (d.url) {
                <a [href]="d.url" target="_blank" style="color: var(--primary); font-size: 18px;">
                  <span class="material-icons" style="font-size: 16px;">open_in_new</span>
                </a>
              }
            </div>
            <p style="color: var(--text-secondary); margin-top: 4px; font-size: 12px;">
              {{ d.conteudo | slice:0:200 }}{{ d.conteudo.length > 200 ? '...' : '' }}
            </p>
          </div>
        }
      </div>
    }
  `,
  styles: [`
    .agente-progresso {
      padding: 16px; background: #e3f2fd; border-radius: 12px;
      border: 1px solid rgba(33,150,243,0.2); margin-top: 12px;
    }
    .progresso-header {
      display: flex; align-items: center; gap: 8px; font-size: 14px;
      font-weight: 600; color: var(--primary); margin-bottom: 12px;
    }
    .agente-resultado {
      padding: 16px; background: #e8f5e9; border-radius: 12px;
      border: 1px solid rgba(76,175,80,0.2); margin-top: 12px;
    }
    .resultado-header {
      display: flex; align-items: center; gap: 10px; font-size: 14px; margin-bottom: 12px;
    }
    .passos-list { display: flex; flex-direction: column; gap: 6px; }
    .passo-item {
      display: flex; align-items: center; gap: 6px;
      font-size: 13px; padding: 4px 0;
    }
    .passo-resultado {
      padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    .passo-resultado:last-child { border: none; }
    .passo-fonte {
      font-size: 10px; padding: 2px 8px; border-radius: 10px;
      background: rgba(33,150,243,0.1); color: var(--primary);
    }
    .spin { animation: spin 1.5s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    details summary { list-style: none; }
    details summary::-webkit-details-marker { display: none; }
    .detalhe-toggle {
      cursor: pointer; display: flex; align-items: center; gap: 6px;
      font-size: 13px; font-weight: 600; color: var(--primary);
      padding: 6px 0;
    }
    .detalhe-conteudo {
      margin: 6px 0 6px 22px; padding: 8px 12px;
      background: rgba(255,255,255,0.7); border-radius: 8px;
      border: 1px solid rgba(0,0,0,0.06);
    }
    .detalhe-item {
      font-size: 12px; padding: 4px 0;
      border-bottom: 1px solid rgba(0,0,0,0.04);
    }
    .detalhe-item:last-child { border: none; }
    .dado-item {
      padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.06);
    }
    .dado-item:last-child { border: none; }
    .qa-item {
      padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,0.06);
    }
    .qa-item:last-child { border: none; }
  `],
})
export class ScrapingComponent {
  // Agente inteligente
  tema = '';
  carregandoAgente = false;
  resultadoAgente: any = null;
  progressoMensagens: string[] = [];
  passoAtual = '';
  erro = '';

  // Busca manual
  fonte = 'pubmed';
  termoManual = '';
  maxResultados = 10;
  dados: DadoMedico[] = [];
  carregando = false;
  carregandoTodas = false;

  // URL livre
  urlLivre = '';
  carregandoUrl = false;
  resultadoUrl: any = null;

  // Dataset
  enviandoDataset = false;
  mensagemDataset = '';

  fontes = [
    { value: 'pubmed', label: 'PubMed' },
    { value: 'medlineplus', label: 'MedlinePlus' },
    { value: 'bvs', label: 'BVS/BIREME' },
    { value: 'drauzio', label: 'Drauzio Varella' },
    { value: 'mayo_clinic', label: 'Mayo Clinic' },
    { value: 'datasus', label: 'DataSUS' },
    { value: 'openfda', label: 'OpenFDA' },
  ];

  constructor(private api: ApiService) {}

  executarAgente(): void {
    this.carregandoAgente = true;
    this.resultadoAgente = null;
    this.erro = '';
    this.progressoMensagens = [];

    const etapas = [
      'Planejando pesquisa com IA...',
      'Buscando artigos no PubMed...',
      'Consultando fontes brasileiras...',
      'Pesquisando artigos academicos...',
      'Salvando dados coletados...',
      'Gerando dataset com IA...',
    ];

    let idx = 0;
    this.passoAtual = etapas[0];
    const interval = setInterval(() => {
      if (idx < etapas.length - 1) {
        this.progressoMensagens.push(etapas[idx]);
        idx++;
        this.passoAtual = etapas[idx];
      }
    }, 4000);

    this.api.agenteInteligente(this.tema).subscribe({
      next: (res) => {
        clearInterval(interval);
        this.resultadoAgente = res;
        this.carregandoAgente = false;
        this.progressoMensagens = [];
      },
      error: (err) => {
        clearInterval(interval);
        this.erro = err.error?.detail || 'Erro no agente inteligente.';
        this.carregandoAgente = false;
      },
    });
  }

  buscarManual(): void {
    this.carregando = true;
    this.erro = '';
    this.api.buscarDados(this.fonte, this.termoManual, this.maxResultados).subscribe({
      next: (dados) => { this.dados = dados; this.carregando = false; },
      error: (err) => { this.erro = err.error?.detail || 'Erro na busca.'; this.carregando = false; },
    });
  }

  buscarTodas(): void {
    this.carregandoTodas = true;
    this.erro = '';
    this.api.buscarTodasFontes(this.termoManual).subscribe({
      next: (dados) => { this.dados = dados; this.carregandoTodas = false; },
      error: (err) => { this.erro = err.error?.detail || 'Erro.'; this.carregandoTodas = false; },
    });
  }

  scrapingUrl(): void {
    this.carregandoUrl = true;
    this.resultadoUrl = null;
    this.erro = '';
    this.api.scrapingUrlLivre(this.urlLivre).subscribe({
      next: (r) => { this.resultadoUrl = r; this.carregandoUrl = false; },
      error: (err) => { this.erro = err.error?.detail || 'Erro ao acessar URL.'; this.carregandoUrl = false; },
    });
  }

  enviarParaDataset(): void {
    this.enviandoDataset = true;
    this.mensagemDataset = '';
    this.api.enviarParaDataset(this.termoManual || this.tema).subscribe({
      next: (r) => {
        this.enviandoDataset = false;
        this.mensagemDataset = `${r.entradas_criadas} entradas enviadas para o dataset!`;
        setTimeout(() => this.mensagemDataset = '', 8000);
      },
      error: (err) => { this.enviandoDataset = false; this.erro = err.error?.detail || 'Erro.'; },
    });
  }
}
