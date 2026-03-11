import { Routes } from '@angular/router';
import { ChatComponent } from './components/chat/chat.component';
import { TriagemComponent } from './components/triagem/triagem.component';
import { ProntuarioComponent } from './components/prontuario/prontuario.component';
import { ConfigComponent } from './components/config/config.component';
import { ScrapingComponent } from './components/scraping/scraping.component';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  { path: 'chat', component: ChatComponent },
  { path: 'triagem', component: TriagemComponent },
  { path: 'prontuario', component: ProntuarioComponent },
  { path: 'config', component: ConfigComponent },
  { path: 'scraping', component: ScrapingComponent },
];
