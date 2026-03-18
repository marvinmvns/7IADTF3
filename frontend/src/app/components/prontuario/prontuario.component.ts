import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { FichaPaciente, Paciente } from '../../models/models';

@Component({
  selector: 'app-prontuario',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle;">folder_shared</span>
        Prontuario do Paciente
      </h2>

      <div style="display: flex; gap: 8px; margin-bottom: 16px; position: relative;">
        <div style="flex: 1; max-width: 400px; position: relative;">
          <input class="form-control" [(ngModel)]="busca" placeholder="CPF ou nome do paciente..."
                 (input)="onBuscaInput()" (keyup.enter)="buscarDireto()"
                 (focus)="mostrarSugestoes = sugestoes.length > 0" autocomplete="off">
          @if (mostrarSugestoes && sugestoes.length > 0) {
            <div class="autocomplete-dropdown">
              @for (p of sugestoes; track p.id) {
                <div class="autocomplete-item" (mousedown)="selecionarPaciente(p)">
                  <span class="material-icons" style="font-size: 20px; color: var(--primary);">person</span>
                  <div>
                    <div style="font-weight: 500; font-size: 13px;">{{ p.nome }}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">CPF: {{ p.cpf }} | Nasc: {{ p.data_nascimento }}</div>
                  </div>
                </div>
              }
            </div>
          }
        </div>
        <button class="btn btn-primary" (click)="buscarDireto()" [disabled]="!busca || carregando">
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

    <!-- Modal confirmação data de nascimento -->
    @if (pacienteParaConfirmar) {
      <div class="modal-overlay" (click)="fecharModal($event)">
        <div class="modal-content" style="max-width: 400px; text-align: center;">
          <div style="margin-bottom: 16px;">
            <span class="material-icons" style="font-size: 48px; color: var(--primary); opacity: 0.6;">verified_user</span>
          </div>
          <h3 style="font-size: 16px; margin-bottom: 4px;">Confirmar identidade</h3>
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
            Paciente: <strong>{{ pacienteParaConfirmar.nome }}</strong>
          </p>
          <div class="form-group">
            <label>Informe a data de nascimento para confirmar</label>
            <input class="form-control" type="date" [(ngModel)]="dataNascConfirmacao"
                   (keyup.enter)="confirmarIdentidade()" style="text-align: center; font-size: 16px;">
          </div>
          @if (erroConfirmacao) {
            <div style="padding: 8px; background: #fce4ec; border-radius: 8px; color: var(--danger); font-size: 13px; margin-bottom: 12px;">
              <span class="material-icons" style="font-size: 14px; vertical-align: middle;">error</span>
              {{ erroConfirmacao }}
            </div>
          }
          <div style="display: flex; gap: 8px; justify-content: center;">
            <button class="btn btn-primary" (click)="confirmarIdentidade()" [disabled]="!dataNascConfirmacao">
              <span class="material-icons">check</span> Confirmar
            </button>
            <button class="btn btn-outline" (click)="pacienteParaConfirmar = undefined; erroConfirmacao = ''">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    }

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

      <!-- Prontuarios -->
      <div class="card fade-in">
        <h3 style="font-size: 16px; margin-bottom: 12px;">
          Historico de Consultas ({{ ficha.prontuarios.length }})
        </h3>
        @if (ficha.prontuarios.length === 0) {
          <p style="color: var(--text-secondary);">Nenhum prontuario registrado.</p>
        }
        @for (p of ficha.prontuarios; track p.id) {
          <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <strong>{{ p.diagnostico }}</strong>
              <span style="font-size: 12px; color: var(--text-secondary);">{{ p.data_consulta | date:'dd/MM/yyyy' }}</span>
            </div>
            <div style="font-size: 13px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px;">
              <div><strong>Medico:</strong> {{ p.medico_responsavel }}</div>
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
          Historico de Triagens ({{ ficha.triagens.length }})
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
              @if (t.temperatura) { <span>Temp: {{ t.temperatura }}C</span> }
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
  styles: [`
    .autocomplete-dropdown {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
      background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.12); max-height: 250px; overflow-y: auto;
    }
    .autocomplete-item {
      display: flex; align-items: center; gap: 10px;
      padding: 10px 12px; cursor: pointer; transition: background 0.15s;
    }
    .autocomplete-item:hover { background: var(--bg); }
    .autocomplete-item:not(:last-child) { border-bottom: 1px solid var(--border); }
    .modal-overlay {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.5); z-index: 100;
      display: flex; align-items: center; justify-content: center;
      animation: fadeIn 0.2s ease; padding: 20px;
    }
    .modal-content {
      background: var(--surface); border-radius: 16px;
      padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      animation: slideUp 0.25s ease;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
  `],
})
export class ProntuarioComponent implements OnInit {
  busca = '';
  cpf = '';
  ficha?: FichaPaciente;
  carregando = false;
  erro = '';

  todosPacientes: Paciente[] = [];
  sugestoes: Paciente[] = [];
  mostrarSugestoes = false;

  pacienteParaConfirmar?: Paciente;
  dataNascConfirmacao = '';
  erroConfirmacao = '';

  constructor(private api: ApiService, private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.api.listarPacientes().subscribe(p => this.todosPacientes = p);

    this.route.queryParams.subscribe(params => {
      if (params['cpf']) {
        this.busca = params['cpf'];
        this.cpf = params['cpf'];
        this.buscarPorCpf(params['cpf']);
        return;
      }
    });

    const saved = sessionStorage.getItem('medassist_prontuario');
    if (saved) {
      try {
        const d = JSON.parse(saved);
        this.busca = d.cpf || '';
        this.cpf = d.cpf || '';
        this.ficha = d.ficha;
      } catch {}
    }
  }

  onBuscaInput(): void {
    const termo = this.busca.trim();
    if (termo.length < 2) {
      this.sugestoes = [];
      this.mostrarSugestoes = false;
      return;
    }

    const termoNum = termo.replace(/\D/g, '');

    // Busca por CPF ou nome
    this.sugestoes = this.todosPacientes.filter(p => {
      if (termoNum.length >= 2) {
        return p.cpf.replace(/\D/g, '').includes(termoNum);
      }
      return p.nome.toLowerCase().includes(termo.toLowerCase());
    }).slice(0, 6);

    this.mostrarSugestoes = this.sugestoes.length > 0;
  }

  selecionarPaciente(p: Paciente): void {
    this.mostrarSugestoes = false;
    this.sugestoes = [];
    this.busca = p.nome;

    // Se buscou por nome, pede confirmação da data de nascimento
    this.pacienteParaConfirmar = p;
    this.dataNascConfirmacao = '';
    this.erroConfirmacao = '';
  }

  confirmarIdentidade(): void {
    if (!this.pacienteParaConfirmar || !this.dataNascConfirmacao) return;

    if (this.dataNascConfirmacao === this.pacienteParaConfirmar.data_nascimento) {
      // Confirmado — busca a ficha
      this.cpf = this.pacienteParaConfirmar.cpf;
      this.busca = this.pacienteParaConfirmar.cpf;
      this.pacienteParaConfirmar = undefined;
      this.erroConfirmacao = '';
      this.buscarPorCpf(this.cpf);
    } else {
      this.erroConfirmacao = 'Data de nascimento incorreta. Tente novamente.';
    }
  }

  buscarDireto(): void {
    const termo = this.busca.trim();
    if (!termo) return;

    // Se parece CPF (tem números suficientes), busca direto
    const numeros = termo.replace(/\D/g, '');
    if (numeros.length >= 11) {
      this.cpf = termo;
      this.buscarPorCpf(termo);
      return;
    }

    // Se é nome, procura na lista e pede confirmação
    const match = this.todosPacientes.find(p =>
      p.nome.toLowerCase() === termo.toLowerCase()
    );
    if (match) {
      this.selecionarPaciente(match);
    } else {
      this.erro = 'Paciente nao encontrado. Use CPF ou nome completo.';
    }
  }

  private buscarPorCpf(cpf: string): void {
    this.carregando = true;
    this.erro = '';
    this.ficha = undefined;

    this.api.fichaCompleta(cpf).subscribe({
      next: (ficha) => {
        this.ficha = ficha;
        this.carregando = false;
        sessionStorage.setItem('medassist_prontuario', JSON.stringify({ cpf, ficha }));
      },
      error: () => {
        this.erro = 'Paciente nao encontrado com este CPF.';
        this.carregando = false;
      },
    });
  }

  fecharModal(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.pacienteParaConfirmar = undefined;
      this.erroConfirmacao = '';
    }
  }
}
