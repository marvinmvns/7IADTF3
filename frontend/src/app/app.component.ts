import { Component, OnInit, OnDestroy } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <button class="mobile-menu-btn btn-icon" (click)="menuAberto = !menuAberto">
      <span class="material-icons">menu</span>
    </button>

    <div class="app-layout">
      <nav class="app-sidebar" [class.open]="menuAberto">
        <div style="padding: 20px; border-bottom: 1px solid var(--border);">
          @if (mostrarLogo) {
            <div class="logo-container fade-in">
              <img src="assets/logo.gif" alt="MedAssist" style="width: 100%; height: auto;">
            </div>
          } @else {
            <h2 style="font-size: 18px; color: var(--primary);">
              <span class="material-icons" style="vertical-align: middle;">local_hospital</span>
              MedAssist
            </h2>
          }
          @if (!mostrarLogo) {
            <p style="font-size: 12px; color: var(--text-secondary);">Assistente Medico Virtual</p>
          }
        </div>

        <div style="flex: 1; padding: 12px;">
          @for (item of menu; track item.rota) {
            <a [routerLink]="item.rota" routerLinkActive="active"
               class="nav-item" (click)="menuAberto = false">
              <span class="material-icons">{{ item.icone }}</span>
              {{ item.label }}
            </a>
          }
        </div>

        <div style="padding: 16px; border-top: 1px solid var(--border); font-size: 11px; color: var(--text-secondary);">
          Tech Challenge Fase 3 - FIAP
        </div>
      </nav>

      <main class="app-main">
        <router-outlet />
      </main>
    </div>

    @if (menuAberto) {
      <div class="overlay" (click)="menuAberto = false"></div>
    }
  `,
  styles: [`
    .nav-item {
      display: flex; align-items: center; gap: 10px;
      padding: 10px 14px; border-radius: 8px; margin-bottom: 4px;
      color: var(--text); text-decoration: none; font-size: 14px;
      transition: background 0.2s;
    }
    .nav-item:hover { background: var(--bg); }
    .nav-item.active { background: rgba(26,115,232,0.1); color: var(--primary); font-weight: 500; }
    .nav-item .material-icons { font-size: 20px; }
    .logo-container { text-align: center; }
    .overlay {
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 50;
    }
    @media (max-width: 768px) {
      .overlay { display: block; }
    }
  `],
})
export class AppComponent implements OnInit, OnDestroy {
  menuAberto = false;
  mostrarLogo = false;
  private logoInterval: any;

  menu = [
    { rota: '/chat', icone: 'chat', label: 'Chat IA' },
    { rota: '/pacientes', icone: 'people', label: 'Pacientes' },
    { rota: '/triagem', icone: 'emergency', label: 'Triagem' },
    { rota: '/prontuario', icone: 'folder_shared', label: 'Prontuario' },
    { rota: '/scraping', icone: 'travel_explore', label: 'Scraping' },
    { rota: '/finetuning', icone: 'model_training', label: 'Fine-Tuning' },
    { rota: '/auditoria', icone: 'shield', label: 'Trilha de Auditoria' },
    { rota: '/config', icone: 'settings', label: 'Configuracao' },
  ];

  ngOnInit(): void {
    // Mostra logo GIF por 10s a cada 5 minutos
    this.cicloLogo();
    this.logoInterval = setInterval(() => this.cicloLogo(), 5 * 60 * 1000);
  }

  ngOnDestroy(): void {
    if (this.logoInterval) clearInterval(this.logoInterval);
  }

  private cicloLogo(): void {
    this.mostrarLogo = true;
    setTimeout(() => this.mostrarLogo = false, 10000);
  }
}
