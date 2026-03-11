import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ConfigLLM } from '../../models/models';

@Component({
  selector: 'app-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2 style="font-size: 18px; margin-bottom: 16px;">
        <span class="material-icons" style="vertical-align: middle;">settings</span>
        Configuração do LLM e TTS/STT
      </h2>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        <!-- LLM -->
        <div>
          <h3 style="font-size: 15px; margin-bottom: 12px; color: var(--primary);">Modelo de Linguagem (LLM)</h3>
          <div class="form-group">
            <label>Provider</label>
            <select class="form-control" [(ngModel)]="config.provider">
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Modelo</label>
            <input class="form-control" [(ngModel)]="config.model_name"
                   [placeholder]="config.provider === 'openai' ? 'gpt-4o-mini' : 'llama3'">
          </div>
          @if (config.provider === 'openai') {
            <div class="form-group">
              <label>API Key</label>
              <input class="form-control" type="password" [(ngModel)]="apiKey" placeholder="sk-...">
            </div>
          }
          @if (config.provider === 'ollama') {
            <div class="form-group">
              <label>URL do Ollama</label>
              <input class="form-control" [(ngModel)]="config.base_url" placeholder="http://localhost:11434">
            </div>
          }
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label>Temperatura</label>
              <input class="form-control" type="number" [(ngModel)]="config.temperature" min="0" max="2" step="0.1">
            </div>
            <div class="form-group">
              <label>Max Tokens</label>
              <input class="form-control" type="number" [(ngModel)]="config.max_tokens" min="256" max="8192">
            </div>
          </div>
        </div>

        <!-- TTS/STT -->
        <div>
          <h3 style="font-size: 15px; margin-bottom: 12px; color: var(--primary);">Voz (TTS/STT)</h3>
          <div class="form-group">
            <label>Engine TTS (Texto para Voz)</label>
            <select class="form-control" [(ngModel)]="config.tts_engine">
              <option value="piper">Piper (Local, sem GPU)</option>
              <option value="browser">Web Speech API (Navegador)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Engine STT (Voz para Texto)</label>
            <select class="form-control" [(ngModel)]="config.stt_engine">
              <option value="vosk">Vosk (Local, sem GPU)</option>
              <option value="browser">Web Speech API (Navegador)</option>
            </select>
          </div>

          <div style="margin-top: 16px; padding: 12px; background: var(--bg); border-radius: 8px;">
            <strong style="font-size: 13px;">Modelos Locais (sem GPU):</strong>
            <ul style="font-size: 13px; margin-top: 8px; padding-left: 20px;">
              <li><strong>Piper TTS:</strong> pt_BR-faber-medium (ONNX)</li>
              <li><strong>Vosk STT:</strong> vosk-model-pt-br (pequeno)</li>
            </ul>
          </div>
        </div>
      </div>

      <div style="margin-top: 20px; display: flex; gap: 8px;">
        <button class="btn btn-primary" (click)="salvar()" [disabled]="salvando">
          <span class="material-icons">save</span>
          {{ salvando ? 'Salvando...' : 'Salvar Configuração' }}
        </button>
        @if (mensagem) {
          <span style="color: var(--success); font-size: 14px; align-self: center;">{{ mensagem }}</span>
        }
      </div>
    </div>

    @if (configAtual) {
      <div class="card fade-in" style="margin-top: 16px;">
        <h3 style="font-size: 15px; margin-bottom: 12px;">Configuração Ativa</h3>
        <table class="table">
          <tr><td>Provider</td><td><strong>{{ configAtual.provider }}</strong></td></tr>
          <tr><td>Modelo</td><td><strong>{{ configAtual.model_name }}</strong></td></tr>
          <tr><td>Temperatura</td><td>{{ configAtual.temperature }}</td></tr>
          <tr><td>Max Tokens</td><td>{{ configAtual.max_tokens }}</td></tr>
          <tr><td>TTS</td><td>{{ configAtual.tts_engine }}</td></tr>
          <tr><td>STT</td><td>{{ configAtual.stt_engine }}</td></tr>
        </table>
      </div>
    }
  `,
})
export class ConfigComponent implements OnInit {
  config = {
    provider: 'openai',
    model_name: 'gpt-4o-mini',
    base_url: 'http://localhost:11434',
    temperature: 0.7,
    max_tokens: 2048,
    tts_engine: 'piper',
    stt_engine: 'vosk',
  };
  apiKey = '';
  configAtual?: ConfigLLM;
  salvando = false;
  mensagem = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.obterConfig().subscribe({
      next: (cfg) => {
        if (cfg) {
          this.configAtual = cfg;
          this.config = { ...this.config, ...cfg };
        }
      },
    });
  }

  salvar(): void {
    this.salvando = true;
    this.mensagem = '';
    const dados: any = { ...this.config };
    if (this.apiKey) dados.api_key = this.apiKey;

    this.api.salvarConfig(dados).subscribe({
      next: (cfg) => {
        this.configAtual = cfg;
        this.mensagem = 'Configuração salva com sucesso!';
        this.salvando = false;
        setTimeout(() => this.mensagem = '', 3000);
      },
      error: () => { this.mensagem = 'Erro ao salvar'; this.salvando = false; },
    });
  }
}
