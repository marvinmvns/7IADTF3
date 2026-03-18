import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Paciente } from '../../models/models';

@Component({
  selector: 'app-pacientes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
        <div>
          <h2 style="font-size: 18px;">
            <span class="material-icons" style="vertical-align: middle;">people</span>
            Pacientes
          </h2>
          <p style="font-size: 12px; color: var(--text-secondary);">Cadastro e gerenciamento de pacientes</p>
        </div>
        <button class="btn btn-primary" (click)="abrirForm()">
          <span class="material-icons">person_add</span>
          Novo Paciente
        </button>
      </div>

      <!-- Busca -->
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <input class="form-control" [(ngModel)]="termoBusca"
               placeholder="Buscar por nome ou CPF..." (input)="filtrar()"
               style="max-width: 400px;">
        @if (termoBusca) {
          <button class="btn-icon" (click)="termoBusca = ''; filtrar()">
            <span class="material-icons">close</span>
          </button>
        }
        <span style="flex: 1;"></span>
        <span style="font-size: 13px; color: var(--text-secondary); align-self: center;">
          {{ pacientesFiltrados.length }} paciente(s)
        </span>
      </div>

      <!-- Formulario de cadastro -->
      @if (mostrarForm) {
        <div class="card fade-in" style="border: 2px solid var(--primary); margin-bottom: 16px;">
          <h3 style="font-size: 15px; margin-bottom: 16px;">
            <span class="material-icons" style="vertical-align: middle; font-size: 20px;">person_add</span>
            Cadastrar Novo Paciente
          </h3>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
            <div class="form-group">
              <label>Nome Completo *</label>
              <input class="form-control" [(ngModel)]="form.nome" placeholder="Ex: Maria Silva Santos">
            </div>
            <div class="form-group">
              <label>CPF *</label>
              <input class="form-control" [(ngModel)]="form.cpf" placeholder="000.000.000-00"
                     (input)="formatarCPF()" maxlength="14"
                     [style.border-color]="erroCpf ? 'var(--danger)' : ''">
              @if (erroCpf) {
                <div class="field-error">{{ erroCpf }}</div>
              }
            </div>
            <div class="form-group">
              <label>Data de Nascimento *</label>
              <input class="form-control" type="date" [(ngModel)]="form.data_nascimento">
            </div>
            <div class="form-group">
              <label>Sexo *</label>
              <select class="form-control" [(ngModel)]="form.sexo">
                <option value="">Selecione</option>
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
              </select>
            </div>
            <div class="form-group">
              <label>Telefone</label>
              <input class="form-control" [(ngModel)]="form.telefone" placeholder="(00) 00000-0000"
                     (input)="formatarTelefone()" maxlength="15">
            </div>
            <div class="form-group">
              <label>Email</label>
              <input class="form-control" type="email" [(ngModel)]="form.email" placeholder="email@exemplo.com"
                     (blur)="validarEmail()"
                     [style.border-color]="erroEmail ? 'var(--danger)' : ''">
              @if (erroEmail) {
                <div class="field-error">{{ erroEmail }}</div>
              }
            </div>
          </div>

          <!-- CEP e Endereco -->
          <div style="margin-top: 16px;">
            <h4 style="font-size: 14px; margin-bottom: 12px; color: var(--text-secondary);">
              <span class="material-icons" style="vertical-align: middle; font-size: 18px;">location_on</span>
              Endereco
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
              <div class="form-group">
                <label>CEP</label>
                <div style="position: relative;">
                  <input class="form-control" [(ngModel)]="form.cep" placeholder="00000-000"
                         (input)="formatarCEP()" maxlength="9">
                  @if (buscandoCep) {
                    <span style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-size: 12px; color: var(--primary);">
                      Buscando...
                    </span>
                  }
                </div>
                @if (erroCep) {
                  <div class="field-error">{{ erroCep }}</div>
                }
              </div>
              <div class="form-group">
                <label>Endereco</label>
                <input class="form-control" [(ngModel)]="form.endereco" placeholder="Logradouro"
                       [readOnly]="cepPreenchido">
              </div>
              <div class="form-group">
                <label>Bairro</label>
                <input class="form-control" [(ngModel)]="form.bairro" placeholder="Bairro"
                       [readOnly]="cepPreenchido">
              </div>
              <div class="form-group">
                <label>Cidade</label>
                <input class="form-control" [(ngModel)]="form.cidade" placeholder="Cidade"
                       [readOnly]="cepPreenchido">
              </div>
              <div class="form-group">
                <label>Estado</label>
                <input class="form-control" [(ngModel)]="form.estado" placeholder="UF" maxlength="2"
                       [readOnly]="cepPreenchido">
              </div>
            </div>
          </div>

          @if (erroForm) {
            <div style="padding: 10px; background: #fce4ec; border-radius: 8px; color: var(--danger); font-size: 13px; margin-top: 12px;">
              {{ erroForm }}
            </div>
          }

          <div style="display: flex; gap: 8px; margin-top: 16px;">
            <button class="btn btn-primary" (click)="salvar()" [disabled]="salvando || !formValido()">
              <span class="material-icons">save</span>
              {{ salvando ? 'Salvando...' : (editandoId ? 'Salvar Alterações' : 'Cadastrar') }}
            </button>
            <button class="btn btn-outline" (click)="fecharForm()">Cancelar</button>
          </div>
        </div>
      }

      @if (mensagemSucesso) {
        <div class="fade-in" style="padding: 10px 16px; background: #e8f5e9; border-radius: 8px; color: var(--success); font-size: 13px; margin-bottom: 16px; display: flex; align-items: center; gap: 6px;">
          <span class="material-icons" style="font-size: 18px;">check_circle</span>
          {{ mensagemSucesso }}
        </div>
      }

      <!-- Lista de pacientes -->
      @if (carregando) {
        <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
          Carregando pacientes...
        </div>
      } @else if (pacientesFiltrados.length === 0 && !carregando) {
        <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
          <span class="material-icons" style="font-size: 48px; opacity: 0.3;">person_off</span>
          <p style="margin-top: 8px;">
            {{ termoBusca ? 'Nenhum paciente encontrado para essa busca.' : 'Nenhum paciente cadastrado.' }}
          </p>
        </div>
      } @else {
        <div class="pacientes-grid">
          @for (p of pacientesFiltrados; track p.id) {
            <div class="paciente-card" (click)="selecionarPaciente(p)">
              <div class="paciente-avatar">
                <span class="material-icons">{{ p.sexo === 'M' ? 'man' : 'woman' }}</span>
              </div>
              <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; font-size: 14px;">{{ p.nome }}</div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                  CPF: {{ p.cpf }}
                </div>
                <div style="display: flex; gap: 12px; font-size: 12px; color: var(--text-secondary); margin-top: 4px; flex-wrap: wrap;">
                  <span>{{ p.sexo === 'M' ? 'Masc.' : 'Fem.' }}</span>
                  <span>Nasc: {{ p.data_nascimento }}</span>
                  @if (p.telefone) {
                    <span>{{ p.telefone }}</span>
                  }
                </div>
              </div>
              <span class="material-icons" style="color: var(--text-secondary); font-size: 20px;">chevron_right</span>
            </div>
          }
        </div>
      }
    </div>

    <!-- Modal do paciente -->
    @if (pacienteSelecionado) {
      <div class="modal-overlay" (click)="fecharModal($event)">
        <div class="modal-content">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div class="modal-avatar">
                <span class="material-icons">{{ pacienteSelecionado.sexo === 'M' ? 'man' : 'woman' }}</span>
              </div>
              <div>
                <h3 style="font-size: 18px; margin: 0;">{{ pacienteSelecionado.nome }}</h3>
                <p style="font-size: 12px; color: var(--text-secondary); margin: 2px 0 0;">
                  Cadastrado em {{ pacienteSelecionado.criado_em | date:'dd/MM/yyyy' }}
                </p>
              </div>
            </div>
            <button class="btn-icon" (click)="pacienteSelecionado = undefined" title="Fechar">
              <span class="material-icons">close</span>
            </button>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px;">
            <div class="detail-item">
              <span class="detail-label">CPF</span>
              <span class="detail-value">{{ pacienteSelecionado.cpf }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Nascimento</span>
              <span class="detail-value">{{ pacienteSelecionado.data_nascimento }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Sexo</span>
              <span class="detail-value">{{ pacienteSelecionado.sexo === 'M' ? 'Masculino' : 'Feminino' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Telefone</span>
              <span class="detail-value">{{ pacienteSelecionado.telefone || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Email</span>
              <span class="detail-value">{{ pacienteSelecionado.email || '-' }}</span>
            </div>
            @if (pacienteSelecionado.cep) {
              <div class="detail-item">
                <span class="detail-label">CEP</span>
                <span class="detail-value">{{ pacienteSelecionado.cep }}</span>
              </div>
            }
            @if (pacienteSelecionado.endereco) {
              <div class="detail-item" style="grid-column: span 2;">
                <span class="detail-label">Endereco</span>
                <span class="detail-value">{{ pacienteSelecionado.endereco }}</span>
              </div>
            }
            @if (pacienteSelecionado.bairro) {
              <div class="detail-item">
                <span class="detail-label">Bairro</span>
                <span class="detail-value">{{ pacienteSelecionado.bairro }}</span>
              </div>
            }
            @if (pacienteSelecionado.cidade || pacienteSelecionado.estado) {
              <div class="detail-item">
                <span class="detail-label">Cidade/Estado</span>
                <span class="detail-value">{{ pacienteSelecionado.cidade || '' }}{{ pacienteSelecionado.estado ? ' - ' + pacienteSelecionado.estado : '' }}</span>
              </div>
            }
          </div>

          <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; gap: 8px; flex-wrap: wrap;">
            <a class="btn btn-primary" [routerLink]="'/prontuario'" [queryParams]="{cpf: pacienteSelecionado.cpf}" style="text-decoration: none;">
              <span class="material-icons">folder_shared</span>
              Ver Prontuario
            </a>
            <a class="btn btn-outline" [routerLink]="'/chat'" style="text-decoration: none;">
              <span class="material-icons">chat</span>
              Atendimento
            </a>
            <button class="btn btn-outline" (click)="editarPaciente(pacienteSelecionado)">
              <span class="material-icons">edit</span>
              Editar
            </button>
            <div style="flex: 1;"></div>
            <button class="btn btn-danger" (click)="confirmarRemocao(pacienteSelecionado)">
              <span class="material-icons">delete</span>
              Remover
            </button>
          </div>

          @if (confirmandoRemocao) {
            <div style="margin-top: 12px; padding: 12px; background: #fce4ec; border-radius: 8px; border: 1px solid var(--danger);">
              <p style="font-size: 14px; color: var(--danger); margin-bottom: 8px;">
                <strong>Remover {{ pacienteSelecionado.nome }}?</strong>
              </p>
              <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
                Prontuarios, triagens e conversas serao removidos permanentemente.
              </p>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-danger" (click)="removerPaciente()" [disabled]="removendo">
                  <span class="material-icons">delete_forever</span>
                  {{ removendo ? 'Removendo...' : 'Sim, Remover' }}
                </button>
                <button class="btn btn-outline" (click)="confirmandoRemocao = false">Cancelar</button>
              </div>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .pacientes-grid {
      display: flex; flex-direction: column; gap: 8px;
    }
    .paciente-card {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 16px; border: 1px solid var(--border); border-radius: 10px;
      cursor: pointer; transition: all 0.2s;
    }
    .paciente-card:hover {
      border-color: var(--primary); background: rgba(26,115,232,0.03);
    }
    .paciente-avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: var(--bg); display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .paciente-avatar .material-icons { font-size: 22px; color: var(--primary); }

    .detail-item {
      padding: 10px; background: var(--bg); border-radius: 8px;
    }
    .detail-label {
      display: block; font-size: 11px; color: var(--text-secondary);
      text-transform: uppercase; font-weight: 500; margin-bottom: 2px;
    }
    .detail-value { font-size: 14px; font-weight: 500; }

    .modal-overlay {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.5); z-index: 100;
      display: flex; align-items: center; justify-content: center;
      animation: fadeIn 0.2s ease;
      padding: 20px;
    }
    .modal-content {
      background: var(--surface); border-radius: 16px;
      padding: 24px; width: 100%; max-width: 600px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      animation: slideUp 0.25s ease;
      max-height: 90vh; overflow-y: auto;
    }
    .modal-avatar {
      width: 48px; height: 48px; border-radius: 50%;
      background: var(--bg); display: flex; align-items: center; justify-content: center;
    }
    .modal-avatar .material-icons { font-size: 28px; color: var(--primary); }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

    .field-error {
      color: var(--danger); font-size: 12px; margin-top: 4px;
    }
  `],
})
export class PacientesComponent implements OnInit {
  pacientes: Paciente[] = [];
  pacientesFiltrados: Paciente[] = [];
  pacienteSelecionado?: Paciente;
  termoBusca = '';
  carregando = true;
  mostrarForm = false;
  salvando = false;
  erroForm = '';
  mensagemSucesso = '';
  buscandoCep = false;
  cepPreenchido = false;
  erroCpf = '';
  erroEmail = '';
  erroCep = '';
  editandoId?: number;
  confirmandoRemocao = false;
  removendo = false;

  form: {
    nome: string; cpf: string; data_nascimento: string; sexo: string;
    telefone: string; email: string;
    cep: string; endereco: string; bairro: string; cidade: string; estado: string;
  } = {
    nome: '', cpf: '', data_nascimento: '', sexo: '', telefone: '', email: '',
    cep: '', endereco: '', bairro: '', cidade: '', estado: '',
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.carregando = true;
    this.api.listarPacientes().subscribe({
      next: (p) => {
        this.pacientes = p;
        this.filtrar();
        this.carregando = false;
      },
      error: () => this.carregando = false,
    });
  }

  filtrar(): void {
    const termo = this.termoBusca.toLowerCase();
    if (!termo) {
      this.pacientesFiltrados = [...this.pacientes];
    } else {
      this.pacientesFiltrados = this.pacientes.filter(p =>
        p.nome.toLowerCase().includes(termo) ||
        p.cpf.includes(termo)
      );
    }
  }

  abrirForm(): void {
    this.mostrarForm = true;
    this.erroForm = '';
    this.erroCpf = '';
    this.erroEmail = '';
    this.erroCep = '';
    this.cepPreenchido = false;
    this.form = { nome: '', cpf: '', data_nascimento: '', sexo: '', telefone: '', email: '',
                  cep: '', endereco: '', bairro: '', cidade: '', estado: '' };
  }

  fecharForm(): void {
    this.mostrarForm = false;
    this.editandoId = undefined;
    this.erroForm = '';
    this.erroCpf = '';
    this.erroEmail = '';
    this.erroCep = '';
  }

  formValido(): boolean {
    const baseValid = !!(this.form.nome && this.form.cpf && this.form.data_nascimento && this.form.sexo);
    const cpfDigits = this.form.cpf.replace(/\D/g, '');
    const cpfValid = cpfDigits.length === 11;
    const emailValid = !this.form.email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.form.email);
    return baseValid && cpfValid && emailValid && !this.erroCpf && !this.erroEmail;
  }

  formatarCPF(): void {
    let v = this.form.cpf.replace(/\D/g, '');
    if (v.length > 11) v = v.slice(0, 11);
    if (v.length > 9) {
      v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6, 9) + '-' + v.slice(9);
    } else if (v.length > 6) {
      v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6);
    } else if (v.length > 3) {
      v = v.slice(0, 3) + '.' + v.slice(3);
    }
    this.form.cpf = v;

    // Validate CPF length
    const digits = v.replace(/\D/g, '');
    if (digits.length > 0 && digits.length !== 11) {
      this.erroCpf = 'CPF deve ter 11 digitos';
    } else {
      this.erroCpf = '';
    }
  }

  formatarTelefone(): void {
    let v = this.form.telefone.replace(/\D/g, '');
    if (v.length > 11) v = v.slice(0, 11);
    if (v.length > 6) {
      v = '(' + v.slice(0, 2) + ') ' + v.slice(2, 7) + '-' + v.slice(7);
    } else if (v.length > 2) {
      v = '(' + v.slice(0, 2) + ') ' + v.slice(2);
    } else if (v.length > 0) {
      v = '(' + v;
    }
    this.form.telefone = v;
  }

  validarEmail(): void {
    if (this.form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.form.email)) {
      this.erroEmail = 'Formato de email invalido';
    } else {
      this.erroEmail = '';
    }
  }

  formatarCEP(): void {
    let v = this.form.cep.replace(/\D/g, '');
    if (v.length > 8) v = v.slice(0, 8);
    if (v.length > 5) {
      v = v.slice(0, 5) + '-' + v.slice(5);
    }
    this.form.cep = v;
    this.erroCep = '';

    // Auto-fetch when 8 digits
    const digits = v.replace(/\D/g, '');
    if (digits.length === 8) {
      this.buscarEndereco(digits);
    } else {
      this.cepPreenchido = false;
    }
  }

  buscarEndereco(cep: string): void {
    this.buscandoCep = true;
    this.erroCep = '';
    this.api.buscarCep(cep).subscribe({
      next: (data) => {
        this.form.endereco = data.endereco || '';
        this.form.bairro = data.bairro || '';
        this.form.cidade = data.cidade || '';
        this.form.estado = data.estado || '';
        this.form.cep = data.cep || this.form.cep;
        this.cepPreenchido = true;
        this.buscandoCep = false;
      },
      error: () => {
        this.erroCep = 'CEP nao encontrado';
        this.cepPreenchido = false;
        this.buscandoCep = false;
        this.form.endereco = '';
        this.form.bairro = '';
        this.form.cidade = '';
        this.form.estado = '';
      },
    });
  }

  salvar(): void {
    this.salvando = true;
    this.erroForm = '';

    const obs = this.editandoId
      ? this.api.atualizarPaciente(this.editandoId, this.form)
      : this.api.criarPaciente(this.form);

    obs.subscribe({
      next: (p) => {
        if (this.editandoId) {
          const idx = this.pacientes.findIndex(x => x.id === this.editandoId);
          if (idx >= 0) this.pacientes[idx] = p;
          this.mensagemSucesso = `Paciente ${p.nome} atualizado!`;
        } else {
          this.pacientes.unshift(p);
          this.mensagemSucesso = `Paciente ${p.nome} cadastrado!`;
        }
        this.filtrar();
        this.salvando = false;
        this.mostrarForm = false;
        this.editandoId = undefined;
        setTimeout(() => this.mensagemSucesso = '', 5000);
      },
      error: (err) => {
        this.salvando = false;
        const detail = err.error?.detail;
        if (typeof detail === 'string') {
          this.erroForm = detail;
        } else if (Array.isArray(detail)) {
          this.erroForm = detail.map((d: any) => d.msg).join('. ');
        } else {
          this.erroForm = 'Erro ao salvar paciente.';
        }
      },
    });
  }

  selecionarPaciente(p: Paciente): void {
    this.pacienteSelecionado = p;
    this.confirmandoRemocao = false;
  }

  fecharModal(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.pacienteSelecionado = undefined;
      this.confirmandoRemocao = false;
    }
  }

  editarPaciente(p: Paciente): void {
    this.editandoId = p.id;
    this.form = {
      nome: p.nome,
      cpf: p.cpf,
      data_nascimento: p.data_nascimento,
      sexo: p.sexo,
      telefone: p.telefone || '',
      email: p.email || '',
      cep: p.cep || '',
      endereco: p.endereco || '',
      bairro: p.bairro || '',
      cidade: p.cidade || '',
      estado: p.estado || '',
    };
    this.mostrarForm = true;
    this.erroForm = '';
    this.pacienteSelecionado = undefined;
  }

  confirmarRemocao(p: Paciente): void {
    this.confirmandoRemocao = true;
  }

  removerPaciente(): void {
    if (!this.pacienteSelecionado) return;
    this.removendo = true;
    this.api.removerPaciente(this.pacienteSelecionado.id).subscribe({
      next: () => {
        this.pacientes = this.pacientes.filter(p => p.id !== this.pacienteSelecionado!.id);
        this.filtrar();
        this.mensagemSucesso = `Paciente ${this.pacienteSelecionado!.nome} removido.`;
        this.pacienteSelecionado = undefined;
        this.confirmandoRemocao = false;
        this.removendo = false;
        setTimeout(() => this.mensagemSucesso = '', 5000);
      },
      error: (err) => {
        this.erroForm = err.error?.detail || 'Erro ao remover paciente.';
        this.removendo = false;
      },
    });
  }
}
