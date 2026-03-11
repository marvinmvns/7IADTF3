import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { FichaPaciente } from '../../models/models';

@Component({
  selector: 'app-prontuario',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle;">folder_shared</span>
        Prontuário do Paciente
      </h2>

      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <input class="form-control" [(ngModel)]="cpf" placeholder="Digite o CPF do paciente"
               (keyup.enter)="buscar()" style="max-width: 300px;">
        <button class="btn btn-primary" (click)="buscar()" [disabled]="!cpf || carregando">
          <span class="material-icons">search</span>
          {{ carregando ? 'Buscando...' : 'Buscar' }}
        </button>
      </div>

      @if (erro) {
        <div style="padding: 16px; background: #fce4ec; border-radius: 8px; color: var(--danger);">
          {{ erro }}
        </div>
      }
    </div>

    @if (ficha) {
      <!-- Dados do Paciente -->
      <div class="card fade-in">
        <h3 style="font-size: 16px; margin-bottom: 12px;">Dados Pessoais</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
          <div><strong>Nome:</strong> {{ ficha.paciente.nome }}</div>
          <div><strong>CPF:</strong> {{ ficha.paciente.cpf }}</div>
          <div><strong>Nascimento:</strong> {{ ficha.paciente.data_nascimento }}</div>
          <div><strong>Sexo:</strong> {{ ficha.paciente.sexo === 'M' ? 'Masculino' : 'Feminino' }}</div>
          <div><strong>Telefone:</strong> {{ ficha.paciente.telefone || '-' }}</div>
          <div><strong>Email:</strong> {{ ficha.paciente.email || '-' }}</div>
        </div>
      </div>

      <!-- Prontuários / Histórico -->
      <div class="card fade-in">
        <h3 style="font-size: 16px; margin-bottom: 12px;">
          Histórico de Consultas ({{ ficha.prontuarios.length }})
        </h3>
        @if (ficha.prontuarios.length === 0) {
          <p style="color: var(--text-secondary);">Nenhum prontuário registrado.</p>
        }
        @for (p of ficha.prontuarios; track p.id) {
          <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <strong>{{ p.diagnostico }}</strong>
              <span style="font-size: 12px; color: var(--text-secondary);">{{ p.data_consulta | date:'dd/MM/yyyy' }}</span>
            </div>
            <div style="font-size: 13px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px;">
              <div><strong>Médico:</strong> {{ p.medico_responsavel }}</div>
              <div><strong>Medicamentos:</strong> {{ p.medicamentos || '-' }}</div>
              <div><strong>Alergias:</strong> {{ p.alergias || '-' }}</div>
              @if (p.observacoes) {
                <div style="grid-column: 1 / -1;"><strong>Obs:</strong> {{ p.observacoes }}</div>
              }
            </div>
          </div>
        }
      </div>

      <!-- Triagens -->
      <div class="card fade-in">
        <h3 style="font-size: 16px; margin-bottom: 12px;">
          Histórico de Triagens ({{ ficha.triagens.length }})
        </h3>
        @if (ficha.triagens.length === 0) {
          <p style="color: var(--text-secondary);">Nenhuma triagem registrada.</p>
        }
        @for (t of ficha.triagens; track t.id) {
          <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
              <span class="badge badge-{{ t.classificacao_risco }}">{{ t.classificacao_risco }}</span>
              <span style="font-size: 12px; color: var(--text-secondary);">{{ t.criado_em | date:'dd/MM/yyyy HH:mm' }}</span>
              @if (t.validado_por_humano) {
                <span class="badge badge-verde" style="font-size: 10px;">Validado</span>
              }
            </div>
            <p style="font-size: 13px;"><strong>Sintomas:</strong> {{ t.sintomas }}</p>
            <div style="font-size: 13px; display: flex; gap: 16px; margin-top: 4px; flex-wrap: wrap;">
              @if (t.pressao_arterial) { <span>PA: {{ t.pressao_arterial }}</span> }
              @if (t.temperatura) { <span>Temp: {{ t.temperatura }}°C</span> }
              @if (t.frequencia_cardiaca) { <span>FC: {{ t.frequencia_cardiaca }} bpm</span> }
              @if (t.saturacao) { <span>SpO2: {{ t.saturacao }}%</span> }
            </div>
            @if (t.orientacao_ia) {
              <div style="margin-top: 8px; padding: 8px; background: var(--bg); border-radius: 6px; font-size: 13px;">
                <strong>IA:</strong> {{ t.orientacao_ia }}
              </div>
            }
          </div>
        }
      </div>
    }
  `,
})
export class ProntuarioComponent {
  cpf = '';
  ficha?: FichaPaciente;
  carregando = false;
  erro = '';

  constructor(private api: ApiService) {}

  buscar(): void {
    this.carregando = true;
    this.erro = '';
    this.ficha = undefined;

    this.api.fichaCompleta(this.cpf).subscribe({
      next: (ficha) => { this.ficha = ficha; this.carregando = false; },
      error: () => { this.erro = 'Paciente não encontrado com este CPF.'; this.carregando = false; },
    });
  }
}
