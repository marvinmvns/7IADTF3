import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Mensagem, Paciente, FichaPaciente } from '../../models/models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <!-- Barra do médico -->
    @if (!medicoIdentificado) {
      <div class="card">
        <h2 style="font-size: 18px; margin-bottom: 16px;">
          <span class="material-icons" style="vertical-align: middle; color: var(--primary);">badge</span>
          Identificação do Médico
        </h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; max-width: 500px;">
          <div class="form-group">
            <label>CRM</label>
            <input class="form-control" [(ngModel)]="crm" placeholder="00000-UF" (keyup.enter)="identificarMedico()">
          </div>
          <div class="form-group">
            <label>Nome do Médico</label>
            <input class="form-control" [(ngModel)]="nomeMedico" placeholder="Dr(a). Nome" (keyup.enter)="identificarMedico()">
          </div>
        </div>
        <button class="btn btn-primary" (click)="identificarMedico()" [disabled]="!crm || !nomeMedico" style="margin-top: 8px;">
          <span class="material-icons">login</span>
          Iniciar Atendimento
        </button>
      </div>
    }

    @if (medicoIdentificado) {
      <!-- Header do atendimento -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 10px 16px; background: var(--surface); border-radius: 10px; border: 1px solid var(--border);">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="material-icons" style="color: var(--primary);">badge</span>
          <div>
            <div style="font-weight: 600; font-size: 14px;">{{ nomeMedico }}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">CRM {{ crm }}</div>
          </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          @if (paciente) {
            <span style="font-size: 12px; padding: 4px 10px; background: #e8f5e9; border-radius: 20px; color: var(--success);">
              Atendendo: {{ paciente.nome }}
            </span>
          }
          <button class="btn-icon" (click)="encerrarSessao()" title="Encerrar sessão">
            <span class="material-icons" style="font-size: 20px; color: var(--danger);">logout</span>
          </button>
        </div>
      </div>

      <!-- Selecionar paciente -->
      @if (!paciente) {
        <div class="card">
          <h3 style="font-size: 15px; margin-bottom: 12px;">
            <span class="material-icons" style="vertical-align: middle;">person_search</span>
            Selecionar Paciente para Atendimento
          </h3>
          <div class="form-group" style="position: relative; max-width: 400px;">
            <input class="form-control" [(ngModel)]="cpfBusca" placeholder="CPF do paciente..."
                   (input)="filtrarPacientes()" (focus)="mostrarLista = sugestoes.length > 0" autocomplete="off">
            @if (mostrarLista && sugestoes.length > 0) {
              <div class="autocomplete-dropdown">
                @for (p of sugestoes; track p.id) {
                  <div class="autocomplete-item" (mousedown)="selecionarPaciente(p)">
                    <span class="material-icons" style="font-size: 20px; color: var(--primary);">person</span>
                    <div>
                      <div style="font-weight: 500; font-size: 13px;">{{ p.nome }}</div>
                      <div style="font-size: 11px; color: var(--text-secondary);">CPF: {{ p.cpf }} | {{ p.sexo === 'M' ? 'Masc.' : 'Fem.' }} | Nasc: {{ p.data_nascimento }}</div>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </div>
      }

      <!-- Layout principal: Chat + Painel clínico -->
      @if (paciente) {
        <div class="atendimento-layout">
          <!-- Painel clínico lateral -->
          <div class="painel-clinico">
            <div class="painel-header">
              <span class="material-icons">medical_information</span>
              Contexto Clínico
              <button class="btn-icon" (click)="trocarPaciente()" title="Trocar paciente" style="margin-left: auto;">
                <span class="material-icons" style="font-size: 18px;">swap_horiz</span>
              </button>
            </div>

            <!-- Dados do paciente -->
            <div class="painel-secao">
              <div class="painel-secao-titulo">
                <span class="material-icons">person</span> Paciente
              </div>
              <div style="font-weight: 600;">{{ paciente.nome }}</div>
              <div class="info-grid">
                <span>CPF: {{ paciente.cpf }}</span>
                <span>{{ paciente.sexo === 'M' ? 'Masculino' : 'Feminino' }}</span>
                <span>Nasc: {{ paciente.data_nascimento }}</span>
                @if (paciente.telefone) { <span>Tel: {{ paciente.telefone }}</span> }
              </div>
            </div>

            <!-- Alergias -->
            @if (alergias.length > 0) {
              <div class="painel-secao alerta-alergias">
                <div class="painel-secao-titulo" style="color: var(--danger);">
                  <span class="material-icons">warning</span> Alergias
                </div>
                @for (a of alergias; track a) {
                  <span class="tag tag-danger">{{ a }}</span>
                }
              </div>
            }

            <!-- Diagnósticos ativos -->
            @if (ficha && ficha.prontuarios.length > 0) {
              <div class="painel-secao">
                <div class="painel-secao-titulo">
                  <span class="material-icons">diagnosis</span> Diagnósticos
                </div>
                @for (pront of ficha.prontuarios; track pront.id) {
                  <div class="diagnostico-item">
                    <div style="font-weight: 500; font-size: 12px;">{{ pront.diagnostico }}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">{{ pront.medico_responsavel }}</div>
                  </div>
                }
              </div>
            }

            <!-- Medicamentos em uso -->
            @if (medicamentos.length > 0) {
              <div class="painel-secao">
                <div class="painel-secao-titulo">
                  <span class="material-icons">medication</span> Medicamentos
                </div>
                @for (m of medicamentos; track m) {
                  <span class="tag tag-med">{{ m }}</span>
                }
              </div>
            }

            <!-- Últimas triagens -->
            @if (ficha && ficha.triagens.length > 0) {
              <div class="painel-secao">
                <div class="painel-secao-titulo">
                  <span class="material-icons">assessment</span> Últimas Triagens
                </div>
                @for (t of ficha.triagens.slice(0, 3); track t.id) {
                  <div class="triagem-item">
                    <span class="badge badge-{{ t.classificacao_risco }}" style="font-size: 10px;">{{ t.classificacao_risco }}</span>
                    <span style="font-size: 11px;">{{ t.sintomas | slice:0:50 }}...</span>
                  </div>
                }
              </div>
            }
          </div>

          <!-- Chat -->
          <div class="chat-area">
            <div class="chat-container card" style="margin: 0;">
              <div class="chat-header" style="padding-bottom: 10px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <h3 style="font-size: 15px; margin: 0;">Apoio à Decisão Clínica</h3>
                  <p style="font-size: 11px; color: var(--text-secondary); margin: 2px 0 0;">
                    IA + RAG + Fine-Tuning | Paciente: {{ paciente.nome }}
                  </p>
                </div>
                <div style="display: flex; gap: 6px; align-items: center;">
                  @if (modoVoz) {
                    <span style="font-size: 10px; color: var(--primary); font-weight: 600;">
                      <span class="material-icons" style="font-size: 12px;">graphic_eq</span> Voz
                    </span>
                  }
                  <select class="form-control" [(ngModel)]="tipoChat" style="width: auto; font-size: 12px; padding: 4px 8px;">
                    <option value="consulta">Consulta</option>
                    <option value="triagem">Triagem</option>
                    <option value="geral">Geral</option>
                  </select>
                  @if (mensagens.length > 0) {
                    <button class="btn-icon" (click)="limparConversa()" title="Nova conversa">
                      <span class="material-icons" style="font-size: 18px;">add_comment</span>
                    </button>
                  }
                </div>
              </div>

              <div class="chat-messages" #chatMessages>
                @if (mensagens.length === 0) {
                  <div style="text-align: center; padding: 30px; color: var(--text-secondary);">
                    <span class="material-icons" style="font-size: 40px; opacity: 0.2;">stethoscope</span>
                    <p style="margin-top: 8px; font-size: 13px;">
                      Assistente de apoio ao atendimento de <strong>{{ paciente.nome }}</strong>.<br>
                      Todo o histórico clínico está carregado como contexto.
                    </p>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; margin-top: 12px;">
                      <button class="sugestao-btn" (click)="usarSugestao('Faça um resumo clínico completo e cronológico deste paciente, cruzando dados de prontuários, triagens e atendimentos. Inclua: evolução dos diagnósticos, medicamentos prescritos ao longo do tempo, alergias, sinais vitais das triagens, classificações de risco e condutas adotadas.')">Resumo clínico</button>
                      <button class="sugestao-btn" (click)="usarSugestao('Quais interações medicamentosas devo considerar?')">Interações</button>
                      <button class="sugestao-btn" (click)="usarSugestao('Sugira exames complementares baseado no quadro atual')">Exames</button>
                      <button class="sugestao-btn" (click)="usarSugestao('Qual a conduta recomendada pelos protocolos?')">Conduta</button>
                    </div>
                  </div>
                }
                @for (msg of mensagens; track msg.id) {
                  <div class="msg fade-in" [class.msg-user]="msg.papel === 'user'" [class.msg-assistant]="msg.papel === 'assistant'">
                    <div class="msg-content" [innerHTML]="renderMarkdown(msg.conteudo)"></div>
                    @if (msg.fonte) {
                      <div class="msg-fonte">
                        @for (part of parseFonte(msg.fonte); track part.label) {
                          <span class="fonte-tag" [class.fonte-rag]="part.isRag" [class.fonte-ft]="part.isFt">
                            <span class="material-icons" style="font-size: 11px; vertical-align: middle;">
                              {{ part.isRag ? 'library_books' : part.isFt ? 'model_training' : 'smart_toy' }}
                            </span>
                            {{ part.label }}
                          </span>
                        }
                      </div>
                    }
                    @if (msg.papel === 'assistant') {
                      <button class="btn-icon" title="Ouvir" (click)="ouvirResposta(msg.conteudo)" style="margin-top: 2px;">
                        <span class="material-icons" style="font-size: 14px;">volume_up</span>
                      </button>
                    }
                  </div>
                }
                @if (carregando) {
                  <div class="msg msg-assistant fade-in">
                    <em style="font-size: 13px;">
                      @if (pensando) {
                        <span class="material-icons spin" style="font-size: 14px; vertical-align: middle;">psychology</span>
                        Pensando...
                      } @else {
                        Analisando...
                      }
                    </em>
                  </div>
                }
              </div>

              <!-- Status do modo voz -->
              @if (modoVoz) {
                <div class="voz-status-bar">
                  <span class="material-icons voz-icon"
                        [class.spin]="vozStatus === 'transcrevendo' || vozStatus === 'pensando'">
                    {{ vozStatus === 'gravando' ? 'mic' : vozStatus === 'transcrevendo' ? 'hearing' : vozStatus === 'pensando' ? 'psychology' : vozStatus === 'falando' ? 'volume_up' : 'graphic_eq' }}
                  </span>
                  <span class="voz-label">
                    {{ vozStatus === 'gravando' ? 'Ouvindo... (clique stop para enviar)' : vozStatus === 'transcrevendo' ? 'Transcrevendo...' : vozStatus === 'pensando' ? 'Analisando...' : vozStatus === 'falando' ? 'Respondendo...' : 'Modo voz ativo' }}
                  </span>
                  <button class="btn-icon" (click)="toggleGravacao()" title="Desativar modo voz" style="margin-left: auto;">
                    <span class="material-icons" style="font-size: 18px; color: var(--danger);">close</span>
                  </button>
                </div>
              }

              <div class="chat-input-area">
                @if (modoVoz && gravando) {
                  <button class="btn btn-danger" (click)="pararGravacao()" style="flex: 1; justify-content: center; animation: pulse 1.5s infinite;">
                    <span class="material-icons">stop</span>
                    Parar e Enviar
                  </button>
                } @else if (modoVoz) {
                  <div style="flex: 1; text-align: center; padding: 10px; color: var(--text-secondary); font-size: 13px;">
                    {{ vozStatus === 'transcrevendo' ? 'Convertendo voz em texto...' : vozStatus === 'pensando' ? 'Gerando resposta...' : vozStatus === 'falando' ? 'Ouca a resposta...' : 'Aguarde...' }}
                  </div>
                } @else {
                  <button class="btn-icon" (click)="toggleGravacao()" title="Ativar modo voz hands-free">
                    <span class="material-icons">mic</span>
                  </button>
                  <div style="flex: 1; position: relative;">
                    <input class="form-control" [(ngModel)]="textoInput" (keyup.enter)="enviarManual()"
                           placeholder="Pergunte sobre o paciente, protocolos, conduta..." [disabled]="carregando"
                           [maxLength]="maxChars" style="width: 100%; padding-right: 60px; font-size: 13px;">
                    <span style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 10px;"
                          [style.color]="textoInput.length > maxChars * 0.9 ? 'var(--danger)' : 'var(--text-secondary)'">
                      {{ textoInput.length }}/{{ maxChars }}
                    </span>
                  </div>
                  <button class="btn btn-primary" (click)="enviarManual()" [disabled]="carregando || !textoInput.trim() || textoInput.length > maxChars">
                    <span class="material-icons">send</span>
                  </button>
                }
              </div>
            </div>
          </div>
        </div>
      }
    }

    <style>
      .atendimento-layout {
        display: grid;
        grid-template-columns: 280px 1fr;
        gap: 12px;
        align-items: start;
      }
      @media (max-width: 900px) {
        .atendimento-layout { grid-template-columns: 1fr; }
      }
      .painel-clinico {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        max-height: calc(100vh - 140px);
        overflow-y: auto;
      }
      .painel-header {
        display: flex; align-items: center; gap: 6px;
        padding: 12px 14px; font-size: 14px; font-weight: 600;
        background: var(--primary); color: white;
      }
      .painel-header .material-icons { font-size: 18px; }
      .painel-secao {
        padding: 10px 14px;
        border-bottom: 1px solid var(--border);
      }
      .painel-secao-titulo {
        display: flex; align-items: center; gap: 4px;
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        color: var(--text-secondary); margin-bottom: 6px; letter-spacing: 0.5px;
      }
      .painel-secao-titulo .material-icons { font-size: 14px; }
      .info-grid {
        display: flex; flex-wrap: wrap; gap: 4px 12px;
        font-size: 11px; color: var(--text-secondary); margin-top: 4px;
      }
      .alerta-alergias {
        background: #fff3e0; border-left: 3px solid var(--danger);
      }
      .tag {
        display: inline-block; padding: 2px 8px; border-radius: 12px;
        font-size: 11px; margin: 2px 2px;
      }
      .tag-danger { background: #fce4ec; color: var(--danger); font-weight: 600; }
      .tag-med { background: #e3f2fd; color: var(--primary); }
      .diagnostico-item {
        padding: 4px 0; border-bottom: 1px solid rgba(0,0,0,0.05);
      }
      .diagnostico-item:last-child { border: none; }
      .triagem-item {
        display: flex; align-items: center; gap: 6px;
        padding: 3px 0; font-size: 12px;
      }
      .chat-area { min-width: 0; }
      .sugestao-btn {
        padding: 6px 12px; border: 1px solid var(--border); border-radius: 20px;
        background: var(--surface); font-size: 12px; cursor: pointer;
        transition: all 0.2s; color: var(--primary);
      }
      .sugestao-btn:hover {
        background: var(--primary); color: white; border-color: var(--primary);
      }
      .autocomplete-dropdown {
        position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
        background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12); max-height: 220px; overflow-y: auto;
      }
      .autocomplete-item {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 12px; cursor: pointer; transition: background 0.15s;
      }
      .autocomplete-item:hover { background: var(--bg); }
      .autocomplete-item:not(:last-child) { border-bottom: 1px solid var(--border); }
      .fonte-ft { background: #f3e5f5 !important; color: #7b1fa2 !important; }
      @keyframes pulse-voice {
        0% { box-shadow: 0 0 0 0 rgba(var(--primary-rgb, 33, 150, 243), 0.4); }
        70% { box-shadow: 0 0 0 8px rgba(var(--primary-rgb, 33, 150, 243), 0); }
        100% { box-shadow: 0 0 0 0 rgba(var(--primary-rgb, 33, 150, 243), 0); }
      }
      .voice-mode { color: var(--primary) !important; border-color: var(--primary) !important; }
      .voz-status-bar {
        display: flex; align-items: center; gap: 8px;
        padding: 8px 16px; background: #e3f2fd; border-top: 1px solid rgba(33,150,243,0.2);
        font-size: 13px; color: var(--primary);
      }
      .voz-icon { font-size: 20px; }
      .voz-label { font-weight: 500; }
      .spin { animation: spin 1.5s linear infinite; }
      @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      .btn-danger { background: var(--danger); color: white; }
      .msg-content { font-size: 14px; line-height: 1.6; }
      .msg-content h2 { font-size: 16px; font-weight: 700; margin: 12px 0 6px; }
      .msg-content h3 { font-size: 15px; font-weight: 700; margin: 10px 0 4px; }
      .msg-content h4 { font-size: 14px; font-weight: 700; margin: 8px 0 4px; color: var(--primary); }
      .msg-content strong { font-weight: 700; }
      .msg-content em { font-style: italic; }
      .msg-content ul { margin: 6px 0; padding-left: 20px; }
      .msg-content li { margin: 3px 0; }
      .msg-content code { background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 4px; font-size: 12px; font-family: monospace; }
      .msg-content p { margin: 4px 0; }
    </style>
  `,
})
export class ChatComponent implements OnInit {
  // Médico
  crm = '';
  nomeMedico = '';
  medicoIdentificado = false;

  // Paciente
  cpfBusca = '';
  todosPacientes: Paciente[] = [];
  sugestoes: Paciente[] = [];
  mostrarLista = false;
  paciente?: Paciente;
  ficha?: FichaPaciente;
  alergias: string[] = [];
  medicamentos: string[] = [];

  // Chat
  mensagens: Mensagem[] = [];
  textoInput = '';
  tipoChat = 'consulta';
  conversaId?: number;
  carregando = false;
  pensando = false;
  gravando = false;
  modoVoz = false;
  maxChars = 2000;
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listarPacientes().subscribe(p => this.todosPacientes = p);

    const saved = sessionStorage.getItem('medassist_chat');
    if (saved) {
      try {
        const d = JSON.parse(saved);
        this.crm = d.crm || '';
        this.nomeMedico = d.nomeMedico || '';
        this.medicoIdentificado = d.medicoIdentificado || false;
        this.conversaId = d.conversaId;
        this.tipoChat = d.tipoChat || 'consulta';
        this.mensagens = d.mensagens || [];
        if (d.paciente) {
          this.paciente = d.paciente;
          this.carregarFicha(d.paciente.cpf);
        }
      } catch {}
    }
  }

  private salvarSessao(): void {
    sessionStorage.setItem('medassist_chat', JSON.stringify({
      crm: this.crm, nomeMedico: this.nomeMedico, medicoIdentificado: this.medicoIdentificado,
      conversaId: this.conversaId, tipoChat: this.tipoChat,
      mensagens: this.mensagens.slice(-50),
      paciente: this.paciente,
    }));
  }

  identificarMedico(): void {
    if (!this.crm || !this.nomeMedico) return;
    this.medicoIdentificado = true;
    this.salvarSessao();
  }

  encerrarSessao(): void {
    this.medicoIdentificado = false;
    this.paciente = undefined;
    this.ficha = undefined;
    this.mensagens = [];
    this.conversaId = undefined;
    this.alergias = [];
    this.medicamentos = [];
    sessionStorage.removeItem('medassist_chat');
  }

  filtrarPacientes(): void {
    const termo = this.cpfBusca.replace(/\D/g, '');
    if (termo.length >= 2) {
      this.sugestoes = this.todosPacientes.filter(p =>
        p.cpf.replace(/\D/g, '').includes(termo) ||
        p.nome.toLowerCase().includes(this.cpfBusca.toLowerCase())
      ).slice(0, 8);
      this.mostrarLista = this.sugestoes.length > 0;
    } else if (this.cpfBusca.length >= 2) {
      this.sugestoes = this.todosPacientes.filter(p =>
        p.nome.toLowerCase().includes(this.cpfBusca.toLowerCase())
      ).slice(0, 8);
      this.mostrarLista = this.sugestoes.length > 0;
    } else {
      this.sugestoes = [];
      this.mostrarLista = false;
    }
  }

  selecionarPaciente(p: Paciente): void {
    this.paciente = p;
    this.mostrarLista = false;
    this.cpfBusca = '';
    this.mensagens = [];
    this.conversaId = undefined;
    this.carregarFicha(p.cpf);
    this.salvarSessao();
  }

  trocarPaciente(): void {
    this.paciente = undefined;
    this.ficha = undefined;
    this.alergias = [];
    this.medicamentos = [];
    this.mensagens = [];
    this.conversaId = undefined;
    this.cpfBusca = '';
    this.salvarSessao();
  }

  carregarFicha(cpf: string): void {
    this.api.fichaCompleta(cpf).subscribe({
      next: (f) => {
        this.ficha = f;
        // Extrair alergias únicas
        const aSet = new Set<string>();
        f.prontuarios.forEach(p => {
          if (p.alergias && p.alergias !== 'Nenhuma conhecida') {
            p.alergias.split(',').forEach(a => aSet.add(a.trim()));
          }
        });
        this.alergias = [...aSet];

        // Extrair medicamentos
        const mSet = new Set<string>();
        f.prontuarios.forEach(p => {
          if (p.medicamentos) {
            p.medicamentos.split(',').forEach(m => mSet.add(m.trim().split(' ')[0]));
          }
        });
        this.medicamentos = [...mSet];
      },
    });
  }

  usarSugestao(texto: string): void {
    this.textoInput = texto;
    this.enviar();
  }

  limparConversa(): void {
    this.mensagens = [];
    this.conversaId = undefined;
    this.textoInput = '';
    this.modoVoz = false;
    this.salvarSessao();
  }

  enviarManual(): void {
    this.modoVoz = false;
    this.enviar();
  }

  enviar(): void {
    const texto = this.textoInput.trim();
    if (!texto || !this.paciente) return;

    const iniciadoPorVoz = this.modoVoz;

    this.mensagens.push({
      id: Date.now(), conversa_id: this.conversaId || 0,
      papel: 'user', conteudo: texto, criado_em: new Date().toISOString(),
    });
    this.textoInput = '';
    this.carregando = true;
    this.pensando = false;

    // Cria mensagem placeholder do assistente para streaming
    const assistantMsg: any = {
      id: Date.now() + 1, conversa_id: this.conversaId || 0,
      papel: 'assistant', conteudo: '', fonte: '', criado_em: new Date().toISOString(),
    };
    this.mensagens.push(assistantMsg);

    const stream = this.api.enviarMensagemStream(
      texto, this.conversaId, this.paciente.id, this.tipoChat,
      this.nomeMedico, this.crm,
    );

    stream.start(
      // onToken: cada pedaço de texto
      (token) => {
        this.pensando = false;
        assistantMsg.conteudo += token;
      },
      // onDone: streaming completo
      (data) => {
        assistantMsg.fonte = data.fonte || '';
        if (data.conversa_id) this.conversaId = data.conversa_id;
        this.carregando = false;
        this.pensando = false;
        this.salvarSessao();
        if (iniciadoPorVoz && assistantMsg.conteudo) {
          this.ouvirResposta(assistantMsg.conteudo, true);
        }
      },
      // onError
      (err) => {
        assistantMsg.conteudo = assistantMsg.conteudo || 'Erro ao processar. Verifique o LLM.';
        this.carregando = false;
        this.pensando = false;
        this.salvarSessao();
      },
      // onThinking: modelo está no modo thinking
      () => {
        this.pensando = true;
      }
    );
  }

  vozStatus = '';  // '', 'gravando', 'transcrevendo', 'pensando', 'falando'

  async toggleGravacao(): Promise<void> {
    if (this.modoVoz) {
      // Desativa modo voz completamente
      this.modoVoz = false;
      this.gravando = false;
      this.vozStatus = '';
      this.mediaRecorder?.stop();
      speechSynthesis.cancel();
      return;
    }

    // Ativa modo voz e começa ciclo
    this.modoVoz = true;
    await this.iniciarGravacao();
  }

  private async iniciarGravacao(): Promise<void> {
    if (!this.modoVoz) return;
    this.vozStatus = 'gravando';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];
      this.mediaRecorder.ondataavailable = (e) => this.audioChunks.push(e.data);
      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.audioChunks, { type: 'audio/wav' });
        stream.getTracks().forEach(t => t.stop());
        if (!this.modoVoz) return;
        this.vozStatus = 'transcrevendo';
        this.api.vozParaTexto(blob).subscribe({
          next: (resp) => {
            if (!this.modoVoz) return;
            this.textoInput = resp.texto;
            if (resp.texto?.trim()) {
              this.vozStatus = 'pensando';
              this.enviar();
            } else {
              // Silêncio — volta a gravar
              setTimeout(() => this.iniciarGravacao(), 500);
            }
          },
          error: () => {
            if (this.modoVoz) setTimeout(() => this.iniciarGravacao(), 1000);
          },
        });
      };
      this.mediaRecorder.start();
      this.gravando = true;

      // Auto-stop após 15 segundos de gravação
      setTimeout(() => {
        if (this.gravando && this.modoVoz) {
          this.mediaRecorder?.stop();
          this.gravando = false;
        }
      }, 15000);
    } catch {
      alert('Permissao de microfone negada');
      this.modoVoz = false;
      this.vozStatus = '';
    }
  }

  pararGravacao(): void {
    if (this.gravando) {
      this.mediaRecorder?.stop();
      this.gravando = false;
    }
  }

  renderMarkdown(text: string): string {
    if (!text) return '';
    let html = text
      // Escape HTML
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      // Headers: ### Header → <h4>
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      // Bold + italic: ***text*** or ___text___
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      // Bold: **text** or __text__
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      // Italic: *text* or _text_
      .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
      .replace(/_([^_\n]+)_/g, '<em>$1</em>')
      // Unordered lists: - item or * item
      .replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>')
      // Ordered lists: 1. item
      .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
      // Wrap consecutive <li> in <ul>
      .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
      // Inline code: `code`
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Line breaks
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
    return `<p>${html}</p>`;
  }

  parseFonte(fonte: string): { label: string; isRag: boolean; isFt: boolean }[] {
    if (!fonte) return [];
    return fonte.split(' | ').map(part => ({
      label: part.trim(),
      isRag: part.startsWith('RAG:'),
      isFt: part.startsWith('Fine-Tuned:'),
    }));
  }

  ouvirResposta(texto: string, continuarCiclo = false): void {
    if (continuarCiclo) this.vozStatus = 'falando';

    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(texto);
      u.lang = 'pt-BR';
      u.rate = 0.95;
      u.onend = () => {
        if (continuarCiclo && this.modoVoz) {
          setTimeout(() => this.iniciarGravacao(), 500);
        }
      };
      speechSynthesis.speak(u);
      return;
    }
    this.api.textoParaVoz(texto).subscribe({
      next: (blob) => {
        const audio = new Audio(URL.createObjectURL(blob));
        audio.onended = () => {
          if (continuarCiclo && this.modoVoz) {
            setTimeout(() => this.iniciarGravacao(), 500);
          }
        };
        audio.play();
      },
    });
  }
}
