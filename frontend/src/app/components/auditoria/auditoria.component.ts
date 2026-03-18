import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-auditoria',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 4px;">
        <span class="material-icons" style="vertical-align: middle; color: var(--primary);">shield</span>
        Trilha de Auditoria
      </h2>
      <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">
        Registro completo de todas as acoes realizadas no sistema
      </p>

      <!-- Stats -->
      @if (stats) {
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-numero">{{ stats.total }}</div>
            <div class="stat-label">Total de Registros</div>
          </div>
          <div class="stat-card">
            <div class="stat-numero">{{ statsEntries.length }}</div>
            <div class="stat-label">Categorias</div>
          </div>
          <div class="stat-card">
            <div class="stat-numero">{{ totalUsuarios }}</div>
            <div class="stat-label">Usuarios</div>
          </div>
        </div>

        <!-- Grafico por categoria -->
        <div style="margin: 16px 0;">
          <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary);">ACOES POR CATEGORIA</h4>
          <div class="categorias-chart">
            @for (entry of statsEntries; track entry[0]) {
              <div class="chart-row" (click)="filtrar(entry[0])" [class.chart-active]="filtroAtivo === entry[0]">
                <div class="chart-label">
                  <span class="material-icons" style="font-size: 14px;">{{ iconeAcao(entry[0]) }}</span>
                  {{ entry[0] }}
                </div>
                <div class="chart-bar-container">
                  <div class="chart-bar" [style.width.%]="(entry[1] / maxCategoria) * 100"
                       [style.background]="corAcao(entry[0])"></div>
                </div>
                <div class="chart-count">{{ entry[1] }}</div>
              </div>
            }
          </div>
        </div>
      }

      <!-- Filtros -->
      <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
        <select class="form-control" [(ngModel)]="filtroAtivo" (ngModelChange)="carregar()" style="width: auto; font-size: 13px;">
          <option value="">Todas as acoes</option>
          @for (cat of categorias; track cat) {
            <option [value]="cat">{{ cat }}</option>
          }
        </select>
        <button class="btn btn-outline" (click)="filtroAtivo = ''; carregar()" style="font-size: 12px; padding: 4px 12px;">
          <span class="material-icons" style="font-size: 14px;">clear_all</span> Limpar
        </button>
        <button class="btn btn-outline" (click)="carregar()" style="font-size: 12px; padding: 4px 12px;">
          <span class="material-icons" style="font-size: 14px;">refresh</span> Atualizar
        </button>
        <div style="flex: 1;"></div>
        <span style="font-size: 12px; color: var(--text-secondary);">{{ logs.length }} registros</span>
      </div>
    </div>

    <!-- Logs -->
    <div class="card" style="margin-top: 12px; padding: 0;">
      @if (carregando) {
        <div style="text-align: center; padding: 40px; color: var(--text-secondary);">Carregando logs...</div>
      } @else if (logs.length === 0) {
        <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
          <span class="material-icons" style="font-size: 48px; opacity: 0.3;">receipt_long</span>
          <p style="margin-top: 8px;">Nenhum registro encontrado.</p>
        </div>
      } @else {
        <div class="logs-table">
          @for (log of logs; track log.id) {
            <div class="log-row">
              <div class="log-icone" [style.background]="corAcao(log.acao) + '20'" [style.color]="corAcao(log.acao)">
                <span class="material-icons" style="font-size: 18px;">{{ iconeAcao(log.acao) }}</span>
              </div>
              <div class="log-body">
                <div class="log-acao">
                  <span class="log-badge" [style.background]="corAcao(log.acao) + '20'" [style.color]="corAcao(log.acao)">
                    {{ log.acao }}
                  </span>
                  @if (log.usuario && log.usuario !== 'sistema') {
                    <span style="font-size: 11px; color: var(--text-secondary);">por {{ log.usuario }}</span>
                  }
                </div>
                <div class="log-detalhes">{{ log.detalhes }}</div>
              </div>
              <div class="log-tempo">
                {{ formatarTempo(log.criado_em) }}
              </div>
            </div>
          }
        </div>

        <!-- Paginacao -->
        @if (logs.length >= limite) {
          <div style="text-align: center; padding: 12px;">
            <button class="btn btn-outline" (click)="carregarMais()" style="font-size: 13px;">
              <span class="material-icons" style="font-size: 16px;">expand_more</span> Carregar mais
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .stats-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;
    }
    .stat-card {
      padding: 14px; background: var(--bg); border-radius: 10px; text-align: center;
    }
    .stat-numero { font-size: 28px; font-weight: 700; color: var(--primary); }
    .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-top: 2px; }
    .categorias-chart { display: flex; flex-direction: column; gap: 4px; }
    .chart-row {
      display: grid; grid-template-columns: 200px 1fr 40px; gap: 8px;
      align-items: center; padding: 4px 8px; border-radius: 6px; cursor: pointer;
      transition: background 0.15s; font-size: 12px;
    }
    .chart-row:hover { background: var(--bg); }
    .chart-row.chart-active { background: rgba(26,115,232,0.08); }
    .chart-label { display: flex; align-items: center; gap: 6px; font-weight: 500; }
    .chart-bar-container { height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; }
    .chart-bar { height: 100%; border-radius: 4px; transition: width 0.5s ease; min-width: 4px; }
    .chart-count { text-align: right; font-weight: 600; color: var(--text-secondary); }
    .logs-table { display: flex; flex-direction: column; }
    .log-row {
      display: flex; align-items: start; gap: 12px; padding: 12px 16px;
      border-bottom: 1px solid var(--border); transition: background 0.15s;
    }
    .log-row:hover { background: var(--bg); }
    .log-row:last-child { border: none; }
    .log-icone {
      width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    .log-body { flex: 1; min-width: 0; }
    .log-acao { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .log-badge {
      font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
    }
    .log-detalhes {
      font-size: 13px; color: var(--text-secondary);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .log-tempo {
      font-size: 11px; color: var(--text-secondary); white-space: nowrap; flex-shrink: 0;
    }
  `],
})
export class AuditoriaComponent implements OnInit {
  logs: any[] = [];
  stats: any = null;
  statsEntries: [string, number][] = [];
  maxCategoria = 1;
  totalUsuarios = 0;
  categorias: string[] = [];
  filtroAtivo = '';
  carregando = false;
  pagina = 0;
  limite = 100;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregar();
    this.api.statsAuditoria().subscribe(s => {
      this.stats = s;
      this.statsEntries = Object.entries(s.por_acao || {}) as [string, number][];
      this.statsEntries.sort((a, b) => b[1] - a[1]);
      this.maxCategoria = this.statsEntries.length ? this.statsEntries[0][1] : 1;
      this.totalUsuarios = Object.keys(s.por_usuario || {}).length;
    });
    this.api.categoriasAuditoria().subscribe(c => this.categorias = c);
  }

  carregar(): void {
    this.carregando = true;
    this.pagina = 0;
    this.api.listarLogs(this.filtroAtivo || undefined, 0, this.limite).subscribe({
      next: (logs) => { this.logs = logs; this.carregando = false; },
      error: () => this.carregando = false,
    });
  }

  carregarMais(): void {
    this.pagina++;
    this.api.listarLogs(this.filtroAtivo || undefined, this.pagina * this.limite, this.limite).subscribe({
      next: (logs) => this.logs = [...this.logs, ...logs],
    });
  }

  filtrar(acao: string): void {
    this.filtroAtivo = this.filtroAtivo === acao ? '' : acao;
    this.carregar();
  }

  iconeAcao(acao: string): string {
    const map: Record<string, string> = {
      'chat_mensagem_usuario': 'chat',
      'chat_resposta': 'smart_toy',
      'triagem_criada': 'emergency',
      'triagem_validada': 'verified',
      'paciente_criado': 'person_add',
      'paciente_atualizado': 'edit',
      'paciente_removido': 'person_remove',
      'paciente_consulta': 'search',
      'paciente_ficha_acessada': 'folder_shared',
      'scraping': 'travel_explore',
      'scraping_todas': 'travel_explore',
      'scraping_url_livre': 'link',
      'scraping_to_dataset': 'model_training',
      'agente_inteligente': 'psychology',
      'agente_navegacao': 'smart_toy',
      'finetuning_iniciado': 'play_circle',
      'finetuning_cancelado': 'cancel',
      'config_atualizada': 'settings',
      'dataset_entrada_adicionada': 'add_circle',
      'dataset_entrada_removida': 'remove_circle',
      'dataset_importado': 'upload_file',
      'dataset_gerado': 'auto_awesome',
    };
    return map[acao] || 'receipt_long';
  }

  corAcao(acao: string): string {
    if (acao.startsWith('chat')) return '#2196f3';
    if (acao.startsWith('triagem')) return '#f44336';
    if (acao.startsWith('paciente')) return '#4caf50';
    if (acao.startsWith('scraping') || acao.startsWith('agente')) return '#ff9800';
    if (acao.startsWith('finetuning') || acao.startsWith('dataset')) return '#9c27b0';
    if (acao.startsWith('config')) return '#607d8b';
    return '#757575';
  }

  formatarTempo(iso: string): string {
    const d = new Date(iso);
    const agora = new Date();
    const diffMs = agora.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Agora';
    if (diffMin < 60) return `${diffMin}min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d`;
    return d.toLocaleDateString('pt-BR');
  }
}
