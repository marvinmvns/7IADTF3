import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Mensagem } from '../../models/models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="chat-container card">
      <div class="chat-header" style="padding-bottom: 12px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 style="font-size: 18px;">Chat com Assistente Médico</h2>
          <p style="font-size: 12px; color: var(--text-secondary);">Converse sobre saúde, triagem e orientações</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <select class="form-control" [(ngModel)]="tipoChat" style="width: auto;">
            <option value="geral">Geral</option>
            <option value="triagem">Triagem</option>
            <option value="consulta">Consulta</option>
          </select>
        </div>
      </div>

      <div class="chat-messages" #chatMessages>
        @if (mensagens.length === 0) {
          <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
            <span class="material-icons" style="font-size: 48px; opacity: 0.3;">smart_toy</span>
            <p style="margin-top: 8px;">Inicie uma conversa com o assistente médico</p>
          </div>
        }
        @for (msg of mensagens; track msg.id) {
          <div class="msg fade-in" [class.msg-user]="msg.papel === 'user'" [class.msg-assistant]="msg.papel === 'assistant'">
            <div>{{ msg.conteudo }}</div>
            @if (msg.fonte) {
              <div class="msg-fonte">{{ msg.fonte }}</div>
            }
            @if (msg.papel === 'assistant') {
              <button class="btn-icon" title="Ouvir resposta" (click)="ouvirResposta(msg.conteudo)" style="margin-top: 4px;">
                <span class="material-icons" style="font-size: 16px;">volume_up</span>
              </button>
            }
          </div>
        }
        @if (carregando) {
          <div class="msg msg-assistant fade-in">
            <em>Digitando...</em>
          </div>
        }
      </div>

      <div class="chat-input-area">
        <button class="btn-icon" [class.recording]="gravando" (click)="toggleGravacao()" title="Gravar voz">
          <span class="material-icons" [class.recording-indicator]="gravando">
            {{ gravando ? 'stop' : 'mic' }}
          </span>
        </button>
        <input class="form-control" [(ngModel)]="textoInput" (keyup.enter)="enviar()"
               placeholder="Digite sua mensagem ou use o microfone..." [disabled]="carregando">
        <button class="btn btn-primary" (click)="enviar()" [disabled]="carregando || !textoInput.trim()">
          <span class="material-icons">send</span>
        </button>
      </div>
    </div>
  `,
})
export class ChatComponent {
  mensagens: Mensagem[] = [];
  textoInput = '';
  tipoChat = 'geral';
  conversaId?: number;
  carregando = false;
  gravando = false;
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];

  constructor(private api: ApiService) {}

  enviar(): void {
    const texto = this.textoInput.trim();
    if (!texto) return;

    // Mensagem visual do usuário
    this.mensagens.push({
      id: Date.now(), conversa_id: this.conversaId || 0,
      papel: 'user', conteudo: texto, criado_em: new Date().toISOString(),
    });
    this.textoInput = '';
    this.carregando = true;

    this.api.enviarMensagem(texto, this.conversaId, undefined, this.tipoChat).subscribe({
      next: (resp) => {
        this.conversaId = resp.conversa_id;
        this.mensagens.push(resp);
        this.carregando = false;
      },
      error: () => {
        this.mensagens.push({
          id: Date.now(), conversa_id: 0, papel: 'assistant',
          conteudo: 'Erro ao processar. Verifique a configuração do LLM.', criado_em: new Date().toISOString(),
        });
        this.carregando = false;
      },
    });
  }

  async toggleGravacao(): Promise<void> {
    if (this.gravando) {
      this.mediaRecorder?.stop();
      this.gravando = false;
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (e) => this.audioChunks.push(e.data);
      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.audioChunks, { type: 'audio/wav' });
        stream.getTracks().forEach(t => t.stop());
        this.api.vozParaTexto(blob).subscribe({
          next: (resp) => { this.textoInput = resp.texto; },
          error: () => { this.textoInput = '[Erro na transcrição]'; },
        });
      };

      this.mediaRecorder.start();
      this.gravando = true;
    } catch {
      alert('Permissão de microfone negada');
    }
  }

  ouvirResposta(texto: string): void {
    // Tenta usar Web Speech API como fallback rápido
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(texto);
      utterance.lang = 'pt-BR';
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
      return;
    }
    // Fallback: API do backend (Piper TTS)
    this.api.textoParaVoz(texto).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        new Audio(url).play();
      },
    });
  }
}
