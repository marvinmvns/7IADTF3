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
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle;">travel_explore</span>
        Scraping de Dados Médicos
      </h2>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div class="form-group">
          <label>Fonte</label>
          <select class="form-control" [(ngModel)]="fonte">
            @for (f of fontes; track f.value) {
              <option [value]="f.value">{{ f.label }}</option>
            }
          </select>
        </div>
        <div class="form-group">
          <label>Termo de Busca</label>
          <input class="form-control" [(ngModel)]="termo" placeholder="Ex: diabetes, hipertensão...">
        </div>
        <div class="form-group">
          <label>Max Resultados</label>
          <input class="form-control" type="number" [(ngModel)]="maxResultados" min="1" max="50">
        </div>
      </div>

      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <button class="btn btn-primary" (click)="buscar()" [disabled]="!termo || carregando">
          <span class="material-icons">search</span>
          {{ carregando ? 'Buscando...' : 'Buscar com Scraper' }}
        </button>
        <button class="btn btn-outline" (click)="executarAgente()" [disabled]="!termo || carregandoAgente">
          <span class="material-icons">smart_toy</span>
          {{ carregandoAgente ? 'Agente navegando...' : 'Executar Agente de Navegação' }}
        </button>
      </div>
    </div>

    @if (resultadoAgente) {
      <div class="card fade-in">
        <h3 style="font-size: 15px; margin-bottom: 8px;">
          Agente de Navegação - {{ resultadoAgente.paginas_coletadas }} páginas coletadas
        </h3>
        @for (r of resultadoAgente.resultados; track r.url) {
          <div style="padding: 10px; border-bottom: 1px solid var(--border);">
            <a [href]="r.url" target="_blank" style="font-weight: 500; color: var(--primary);">{{ r.titulo }}</a>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">{{ r.conteudo_preview }}</p>
          </div>
        }
      </div>
    }

    @if (dados.length > 0) {
      <div class="card fade-in">
        <h3 style="font-size: 15px; margin-bottom: 12px;">Resultados ({{ dados.length }})</h3>
        @for (d of dados; track d.id) {
          <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
              <div>
                <strong style="font-size: 14px;">{{ d.titulo }}</strong>
                <span class="badge badge-azul" style="margin-left: 8px; font-size: 10px;">{{ d.fonte }}</span>
              </div>
              @if (d.url) {
                <a [href]="d.url" target="_blank" class="btn-icon" title="Abrir fonte">
                  <span class="material-icons" style="font-size: 18px;">open_in_new</span>
                </a>
              }
            </div>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
              {{ d.conteudo | slice:0:300 }}{{ d.conteudo.length > 300 ? '...' : '' }}
            </p>
          </div>
        }
      </div>
    }
  `,
})
export class ScrapingComponent {
  fonte = 'pubmed';
  termo = '';
  maxResultados = 10;
  dados: DadoMedico[] = [];
  resultadoAgente: any;
  carregando = false;
  carregandoAgente = false;

  fontes = [
    { value: 'pubmed', label: 'PubMed (Artigos Científicos)' },
    { value: 'medlineplus', label: 'MedlinePlus (Saúde)' },
    { value: 'bvs', label: 'BVS/BIREME (Literatura Médica)' },
    { value: 'drauzio', label: 'Drauzio Varella' },
    { value: 'mayo_clinic', label: 'Mayo Clinic' },
    { value: 'datasus', label: 'DataSUS' },
    { value: 'openfda', label: 'OpenFDA (Medicamentos)' },
  ];

  constructor(private api: ApiService) {}

  buscar(): void {
    this.carregando = true;
    this.api.buscarDados(this.fonte, this.termo, this.maxResultados).subscribe({
      next: (dados) => { this.dados = dados; this.carregando = false; },
      error: () => { alert('Erro na busca'); this.carregando = false; },
    });
  }

  executarAgente(): void {
    this.carregandoAgente = true;
    this.api.executarAgente(this.termo).subscribe({
      next: (res) => { this.resultadoAgente = res; this.carregandoAgente = false; },
      error: () => { alert('Erro no agente'); this.carregandoAgente = false; },
    });
  }
}
