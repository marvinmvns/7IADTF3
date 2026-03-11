import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Triagem } from '../../models/models';

@Component({
  selector: 'app-triagem',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle; color: var(--danger);">emergency</span>
        Triagem - Classificação de Risco
      </h2>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
        <div>
          <div class="form-group">
            <label>CPF do Paciente</label>
            <input class="form-control" [(ngModel)]="cpf" placeholder="000.000.000-00" maxlength="14">
          </div>
          <div class="form-group">
            <label>Sintomas / Queixa Principal</label>
            <textarea class="form-control" [(ngModel)]="sintomas" rows="3" placeholder="Descreva os sintomas..."></textarea>
          </div>
        </div>
        <div>
          <div class="form-group">
            <label>Pressão Arterial</label>
            <input class="form-control" [(ngModel)]="pressao" placeholder="120/80">
          </div>
          <div class="form-group">
            <label>Temperatura (°C)</label>
            <input class="form-control" type="number" [(ngModel)]="temperatura" step="0.1" placeholder="36.5">
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label>FC (bpm)</label>
              <input class="form-control" type="number" [(ngModel)]="fc" placeholder="80">
            </div>
            <div class="form-group">
              <label>SpO2 (%)</label>
              <input class="form-control" type="number" [(ngModel)]="spo2" placeholder="98">
            </div>
          </div>
        </div>
      </div>

      <button class="btn btn-primary" (click)="realizarTriagem()" [disabled]="!sintomas || !cpf || carregando" style="margin-top: 12px;">
        <span class="material-icons">assessment</span>
        {{ carregando ? 'Processando...' : 'Realizar Triagem' }}
      </button>
    </div>

    @if (resultado) {
      <div class="card fade-in" style="margin-top: 16px;">
        <h3 style="margin-bottom: 12px;">Resultado da Triagem</h3>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
          <span class="badge badge-{{ resultado.classificacao_risco }}">
            {{ resultado.classificacao_risco }}
          </span>
          <span style="font-size: 14px; color: var(--text-secondary);">
            {{ descricaoRisco[resultado.classificacao_risco] }}
          </span>
        </div>

        @if (resultado.orientacao_ia) {
          <div style="background: var(--bg); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
            <strong style="font-size: 13px;">Orientação da IA:</strong>
            <p style="margin-top: 8px; font-size: 14px; white-space: pre-wrap;">{{ resultado.orientacao_ia }}</p>
          </div>
        }

        <div style="background: #fff3e0; padding: 12px; border-radius: 8px; border-left: 4px solid var(--warning);">
          <strong style="font-size: 13px;">Atenção:</strong>
          <p style="font-size: 13px; margin-top: 4px;">Esta classificação requer validação por profissional de saúde.</p>
        </div>
      </div>
    }
  `,
})
export class TriagemComponent {
  cpf = '';
  sintomas = '';
  pressao = '';
  temperatura?: number;
  fc?: number;
  spo2?: number;
  carregando = false;
  resultado?: Triagem;

  descricaoRisco: Record<string, string> = {
    vermelho: 'Emergência - Atendimento imediato',
    laranja: 'Muito urgente - Até 10 minutos',
    amarelo: 'Urgente - Até 60 minutos',
    verde: 'Pouco urgente - Até 120 minutos',
    azul: 'Não urgente - Até 240 minutos',
  };

  constructor(private api: ApiService) {}

  realizarTriagem(): void {
    this.carregando = true;
    // Primeiro busca paciente por CPF, depois cria triagem
    this.api.buscarPorCpf(this.cpf).subscribe({
      next: (paciente) => {
        this.api.criarTriagem({
          paciente_id: paciente.id,
          sintomas: this.sintomas,
          pressao_arterial: this.pressao || undefined,
          temperatura: this.temperatura,
          frequencia_cardiaca: this.fc,
          saturacao: this.spo2,
        }).subscribe({
          next: (triagem) => { this.resultado = triagem; this.carregando = false; },
          error: () => { alert('Erro ao criar triagem'); this.carregando = false; },
        });
      },
      error: () => { alert('Paciente não encontrado. Cadastre primeiro.'); this.carregando = false; },
    });
  }
}
