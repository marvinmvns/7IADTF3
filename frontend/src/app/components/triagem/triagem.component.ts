import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Triagem, Paciente } from '../../models/models';

@Component({
  selector: 'app-triagem',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle; color: var(--danger);">emergency</span>
        Triagem - Classificacao de Risco
      </h2>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
        <div>
          <div class="form-group" style="position: relative;">
            <label>Buscar Paciente (CPF ou Nome)</label>
            <input class="form-control" [(ngModel)]="busca" placeholder="Digite CPF ou nome do paciente..."
                   (input)="onBuscaInput()" (focus)="mostrarSugestoes = sugestoes.length > 0"
                   (blur)="onBuscaBlur()" autocomplete="off">
            @if (pacienteSelecionado) {
              <div style="margin-top: 4px; padding: 6px 10px; background: #e8f5e9; border-radius: 6px; font-size: 13px; color: var(--success); display: flex; align-items: center; gap: 6px;">
                <span class="material-icons" style="font-size: 16px;">check_circle</span>
                {{ pacienteSelecionado.nome }} — {{ pacienteSelecionado.cpf }}
                <span class="material-icons" style="font-size: 14px; cursor: pointer; margin-left: auto; opacity: 0.6;"
                      (click)="limparPaciente()">close</span>
              </div>
            }
            @if (!pacienteSelecionado && busca.length >= 2 && sugestoes.length === 0 && !mostrarSugestoes) {
              <div style="margin-top: 4px; padding: 6px 10px; background: #fff3e0; border-radius: 6px; font-size: 13px; color: var(--warning); display: flex; align-items: center; gap: 6px;">
                <span class="material-icons" style="font-size: 16px;">info</span>
                Paciente nao encontrado. Preencha os dados manualmente abaixo.
              </div>
            }
            @if (mostrarSugestoes && sugestoes.length > 0) {
              <div class="autocomplete-dropdown">
                @for (p of sugestoes; track p.id) {
                  <div class="autocomplete-item" (mousedown)="selecionarPaciente(p)">
                    <span class="material-icons" style="font-size: 18px; color: var(--primary);">person</span>
                    <div>
                      <div style="font-weight: 500; font-size: 13px;">{{ p.nome }}</div>
                      <div style="font-size: 12px; color: var(--text-secondary);">{{ p.cpf }}</div>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
          @if (!pacienteSelecionado) {
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div class="form-group">
                <label>Nome do Paciente *</label>
                <input class="form-control" [(ngModel)]="nomeManual" placeholder="Nome completo">
              </div>
              <div class="form-group">
                <label>CPF</label>
                <input class="form-control" [(ngModel)]="cpfManual" placeholder="000.000.000-00" maxlength="14"
                       (input)="formatarCpfManual()">
              </div>
            </div>
          }
          <div class="form-group">
            <label>Sintomas / Queixa Principal</label>
            <textarea class="form-control" [(ngModel)]="sintomas" rows="3" placeholder="Descreva os sintomas..."></textarea>
          </div>
        </div>
        <div>
          <div class="form-group">
            <label>Pressao Arterial</label>
            <input class="form-control" [(ngModel)]="pressao" placeholder="120/80"
                   (blur)="validarPressao()"
                   [style.border-color]="erroPressao ? 'var(--danger)' : ''">
            @if (erroPressao) {
              <div class="field-error">{{ erroPressao }}</div>
            }
          </div>
          <div class="form-group">
            <label>Temperatura (C)</label>
            <input class="form-control" type="number" [(ngModel)]="temperatura" step="0.1" placeholder="36.5"
                   (blur)="validarTemperatura()"
                   [style.border-color]="erroTemperatura ? 'var(--danger)' : ''">
            @if (erroTemperatura) {
              <div class="field-error">{{ erroTemperatura }}</div>
            }
            @if (avisoTemperatura) {
              <div class="field-warning">{{ avisoTemperatura }}</div>
            }
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label>FC (bpm)</label>
              <input class="form-control" type="number" [(ngModel)]="fc" placeholder="80"
                     (blur)="validarFC()"
                     [style.border-color]="erroFC ? 'var(--danger)' : ''">
              @if (erroFC) {
                <div class="field-error">{{ erroFC }}</div>
              }
              @if (avisoFC) {
                <div class="field-warning">{{ avisoFC }}</div>
              }
            </div>
            <div class="form-group">
              <label>SpO2 (%)</label>
              <input class="form-control" type="number" [(ngModel)]="spo2" placeholder="98"
                     (blur)="validarSpO2()"
                     [style.border-color]="erroSpO2 ? 'var(--danger)' : ''">
              @if (erroSpO2) {
                <div class="field-error">{{ erroSpO2 }}</div>
              }
              @if (avisoSpO2) {
                <div class="field-warning">{{ avisoSpO2 }}</div>
              }
            </div>
          </div>
        </div>
      </div>

      <button class="btn btn-primary" (click)="realizarTriagem()" [disabled]="!canSubmit() || carregando" style="margin-top: 12px;">
        <span class="material-icons">assessment</span>
        {{ carregando ? 'Processando...' : 'Realizar Triagem' }}
      </button>
    </div>

    @if (resultado) {
      <div class="card fade-in" style="margin-top: 16px;">
        <h3 style="margin-bottom: 12px;">Resultado da Triagem</h3>

        <!-- Classificacao e nivel de urgencia -->
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
          <span class="badge badge-{{ resultado.classificacao_risco }}" style="font-size: 16px; padding: 8px 18px;">
            {{ resultado.classificacao_risco | uppercase }}
          </span>
          <span style="font-size: 14px; color: var(--text-secondary);">
            {{ descricaoRisco[resultado.classificacao_risco] }}
          </span>
          @if (resultado.nivel_urgencia) {
            <span style="font-size: 13px; padding: 4px 12px; background: var(--bg); border-radius: 20px; font-weight: 600;">
              Nivel de urgencia: {{ resultado.nivel_urgencia }}/10
            </span>
          }
        </div>

        <!-- Diagnosticos possiveis -->
        @if (resultado.diagnosticos_possiveis) {
          <div style="background: #e3f2fd; padding: 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid var(--primary);">
            <strong style="font-size: 13px;">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">diagnosis</span>
              Diagnosticos possiveis:
            </strong>
            <ul style="margin: 8px 0 0; padding-left: 20px;">
              @for (d of parseDiagnosticos(resultado.diagnosticos_possiveis); track d) {
                <li style="font-size: 14px; margin: 4px 0;">{{ d }}</li>
              }
            </ul>
          </div>
        }

        <!-- Orientacao da IA (conduta, justificativa, exames, alertas) -->
        @if (resultado.orientacao_ia) {
          <div style="background: var(--bg); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
            <strong style="font-size: 13px;">
              <span class="material-icons" style="font-size: 16px; vertical-align: middle;">smart_toy</span>
              Orientacao da IA:
            </strong>
            @for (parte of parseOrientacao(resultado.orientacao_ia); track parte.label) {
              <div style="margin-top: 8px;">
                <strong style="font-size: 12px; color: var(--text-secondary);">{{ parte.label }}:</strong>
                <p style="margin: 2px 0 0; font-size: 14px;">{{ parte.valor }}</p>
              </div>
            }
          </div>
        }

        <!-- Status de validacao humana -->
        <div style="display: flex; gap: 12px; align-items: stretch; flex-wrap: wrap;">
          @if (!resultado.validado_por_humano) {
            <div style="flex: 1; background: #fff3e0; padding: 12px; border-radius: 8px; border-left: 4px solid var(--warning); display: flex; align-items: center; gap: 10px;">
              <span class="material-icons" style="color: var(--warning);">warning</span>
              <div>
                <strong style="font-size: 13px;">Aguardando validacao humana</strong>
                <p style="font-size: 12px; margin: 2px 0 0; color: var(--text-secondary);">Esta classificacao requer validacao por profissional de saude antes de ser efetivada.</p>
              </div>
            </div>
            <button class="btn btn-primary" (click)="validarTriagem()" style="white-space: nowrap;">
              <span class="material-icons">verified</span>
              Validar Triagem
            </button>
          } @else {
            <div style="flex: 1; background: #e8f5e9; padding: 12px; border-radius: 8px; border-left: 4px solid var(--success); display: flex; align-items: center; gap: 10px;">
              <span class="material-icons" style="color: var(--success);">check_circle</span>
              <div>
                <strong style="font-size: 13px;">Validada por profissional</strong>
                <p style="font-size: 12px; margin: 2px 0 0; color: var(--text-secondary);">Classificacao confirmada e efetivada.</p>
              </div>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .autocomplete-dropdown {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
      background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.12); max-height: 220px; overflow-y: auto;
      margin-top: 2px;
    }
    .autocomplete-item {
      display: flex; align-items: center; gap: 10px;
      padding: 10px 12px; cursor: pointer; transition: background 0.15s;
    }
    .autocomplete-item:hover { background: var(--bg); }
    .autocomplete-item:not(:last-child) { border-bottom: 1px solid var(--border); }
    .field-error {
      color: var(--danger); font-size: 12px; margin-top: 4px;
    }
    .field-warning {
      color: #e65100; font-size: 12px; margin-top: 4px;
      padding: 4px 8px; background: #fff3e0; border-radius: 4px;
      display: flex; align-items: center; gap: 4px;
    }
  `],
})
export class TriagemComponent implements OnInit {
  busca = '';
  cpf = '';
  nomeManual = '';
  cpfManual = '';
  sintomas = '';
  pressao = '';
  temperatura?: number;
  fc?: number;
  spo2?: number;
  carregando = false;
  resultado?: Triagem;

  todosPacientes: Paciente[] = [];
  sugestoes: Paciente[] = [];
  pacienteSelecionado?: Paciente;
  mostrarSugestoes = false;

  // Validation errors
  erroPressao = '';
  erroTemperatura = '';
  erroFC = '';
  erroSpO2 = '';

  // Warnings for critical values
  avisoTemperatura = '';
  avisoFC = '';
  avisoSpO2 = '';

  descricaoRisco: Record<string, string> = {
    vermelho: 'Emergencia - Atendimento imediato',
    laranja: 'Muito urgente - Ate 10 minutos',
    amarelo: 'Urgente - Ate 60 minutos',
    verde: 'Pouco urgente - Ate 120 minutos',
    azul: 'Nao urgente - Ate 240 minutos',
  };

  constructor(private api: ApiService) {
    this.api.listarPacientes().subscribe(p => this.todosPacientes = p);
  }

  ngOnInit(): void {
    const saved = sessionStorage.getItem('medassist_triagem');
    if (saved) {
      try {
        const d = JSON.parse(saved);
        this.cpf = d.cpf || '';
        this.sintomas = d.sintomas || '';
        this.pressao = d.pressao || '';
        this.temperatura = d.temperatura;
        this.fc = d.fc;
        this.spo2 = d.spo2;
        this.resultado = d.resultado;
        if (d.paciente) this.pacienteSelecionado = d.paciente;
      } catch {}
    }
  }

  private salvarSessao(): void {
    sessionStorage.setItem('medassist_triagem', JSON.stringify({
      cpf: this.cpf, sintomas: this.sintomas, pressao: this.pressao,
      temperatura: this.temperatura, fc: this.fc, spo2: this.spo2,
      resultado: this.resultado, paciente: this.pacienteSelecionado,
    }));
  }

  onBuscaInput(): void {
    this.pacienteSelecionado = undefined;
    const termo = this.busca.trim().toLowerCase();

    if (termo.length < 2) {
      this.sugestoes = [];
      this.mostrarSugestoes = false;
      return;
    }

    const termoDigitos = termo.replace(/\D/g, '');

    // Busca por CPF ou nome
    this.sugestoes = this.todosPacientes.filter(p => {
      const cpfMatch = termoDigitos.length >= 2 && p.cpf.replace(/\D/g, '').includes(termoDigitos);
      const nomeMatch = p.nome.toLowerCase().includes(termo);
      return cpfMatch || nomeMatch;
    }).slice(0, 5);

    this.mostrarSugestoes = this.sugestoes.length > 0;

    // Auto-seleciona se CPF completo bate exatamente
    if (termoDigitos.length === 11) {
      const match = this.todosPacientes.find(p => p.cpf.replace(/\D/g, '') === termoDigitos);
      if (match) {
        this.selecionarPaciente(match);
      }
    }
  }

  onBuscaBlur(): void {
    setTimeout(() => this.mostrarSugestoes = false, 200);
  }

  limparPaciente(): void {
    this.pacienteSelecionado = undefined;
    this.busca = '';
    this.nomeManual = '';
    this.cpfManual = '';
  }

  formatarCpfManual(): void {
    let v = this.cpfManual.replace(/\D/g, '');
    if (v.length > 11) v = v.slice(0, 11);
    if (v.length > 9) {
      v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6, 9) + '-' + v.slice(9);
    } else if (v.length > 6) {
      v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6);
    } else if (v.length > 3) {
      v = v.slice(0, 3) + '.' + v.slice(3);
    }
    this.cpfManual = v;
  }

  selecionarPaciente(p: Paciente): void {
    this.busca = p.nome;
    this.cpf = p.cpf;
    this.pacienteSelecionado = p;
    this.mostrarSugestoes = false;
    this.sugestoes = [];
  }

  validarPressao(): void {
    this.erroPressao = '';
    if (!this.pressao) return;
    const regex = /^\d{2,3}\/\d{2,3}$/;
    if (!regex.test(this.pressao.trim())) {
      this.erroPressao = 'Formato invalido. Use o formato 120/80';
    }
  }

  validarTemperatura(): void {
    this.erroTemperatura = '';
    this.avisoTemperatura = '';
    if (this.temperatura == null) return;
    if (this.temperatura < 35 || this.temperatura > 42) {
      this.erroTemperatura = 'Temperatura deve estar entre 35 e 42 C';
    } else if (this.temperatura > 39) {
      this.avisoTemperatura = 'Alerta: Temperatura elevada (> 39 C) - Possivel febre alta';
    }
  }

  validarFC(): void {
    this.erroFC = '';
    this.avisoFC = '';
    if (this.fc == null) return;
    if (this.fc < 30 || this.fc > 250) {
      this.erroFC = 'FC deve estar entre 30 e 250 bpm';
    } else if (this.fc > 120) {
      this.avisoFC = 'Alerta: Frequencia cardiaca elevada (> 120 bpm) - Taquicardia';
    }
  }

  validarSpO2(): void {
    this.erroSpO2 = '';
    this.avisoSpO2 = '';
    if (this.spo2 == null) return;
    if (this.spo2 < 0 || this.spo2 > 100) {
      this.erroSpO2 = 'SpO2 deve estar entre 0 e 100%';
    } else if (this.spo2 < 90) {
      this.avisoSpO2 = 'Alerta: Saturacao baixa (< 90%) - Risco de hipoxemia';
    }
  }

  canSubmit(): boolean {
    const temPaciente = !!this.pacienteSelecionado || !!this.nomeManual.trim();
    return !!(this.sintomas && temPaciente &&
              !this.erroPressao && !this.erroTemperatura && !this.erroFC && !this.erroSpO2);
  }

  parseDiagnosticos(raw: string): string[] {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [raw];
    } catch {
      return [raw];
    }
  }

  parseOrientacao(orientacao: string): { label: string; valor: string }[] {
    return orientacao.split(' | ').map(parte => {
      const idx = parte.indexOf(':');
      if (idx > 0) {
        return { label: parte.slice(0, idx).trim(), valor: parte.slice(idx + 1).trim() };
      }
      return { label: 'Orientacao', valor: parte };
    });
  }

  validarTriagem(): void {
    if (!this.resultado) return;
    this.api.validarTriagem(this.resultado.id).subscribe({
      next: (triagem) => {
        this.resultado = triagem;
        this.salvarSessao();
      },
      error: () => alert('Erro ao validar triagem'),
    });
  }

  realizarTriagem(): void {
    if (!this.pacienteSelecionado && !this.nomeManual.trim()) return;
    this.carregando = true;

    const executar = (pacienteId: number) => {
      this.api.criarTriagem({
        paciente_id: pacienteId,
        sintomas: this.sintomas,
        pressao_arterial: this.pressao || undefined,
        temperatura: this.temperatura,
        frequencia_cardiaca: this.fc,
        saturacao: this.spo2,
      }).subscribe({
        next: (triagem) => { this.resultado = triagem; this.carregando = false; this.salvarSessao(); },
        error: () => { alert('Erro ao criar triagem'); this.carregando = false; },
      });
    };

    if (this.pacienteSelecionado) {
      executar(this.pacienteSelecionado.id);
    } else {
      // Cria paciente novo e depois faz a triagem
      this.api.criarPaciente({
        nome: this.nomeManual.trim(),
        cpf: this.cpfManual || '000.000.000-00',
      }).subscribe({
        next: (p) => {
          this.pacienteSelecionado = p;
          this.busca = p.nome;
          this.todosPacientes.push(p);
          executar(p.id);
        },
        error: () => { alert('Erro ao cadastrar paciente'); this.carregando = false; },
      });
    }
  }
}
