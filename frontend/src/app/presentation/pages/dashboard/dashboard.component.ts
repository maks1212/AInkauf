import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { HttpClient } from '@angular/common/http';

import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <h1>Dashboard</h1>
    <p class="subtitle">Willkommen bei AInkauf – dein smarter Einkaufsoptimierer.</p>

    <div class="status-bar">
      <mat-card appearance="outlined" class="status-card">
        <mat-card-content>
          @if (healthLoading()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <mat-icon [class.ok]="healthOk()" [class.err]="!healthOk()">
              {{ healthOk() ? 'check_circle' : 'error' }}
            </mat-icon>
          }
          <span>Backend API: {{ healthOk() ? 'Online' : 'Offline' }}</span>
        </mat-card-content>
      </mat-card>
    </div>

    <div class="cards">
      <mat-card class="feature-card" routerLink="/nlp">
        <mat-card-header>
          <mat-icon mat-card-avatar class="card-icon">text_fields</mat-icon>
          <mat-card-title>NLP Parser</mat-card-title>
          <mat-card-subtitle>Freitext-Artikel parsen</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <p>Gib z.B. „3kg Äpfel" ein und erhalte strukturierte Daten.</p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button color="primary" routerLink="/nlp">Öffnen</button>
        </mat-card-actions>
      </mat-card>

      <mat-card class="feature-card" routerLink="/detour">
        <mat-card-header>
          <mat-icon mat-card-avatar class="card-icon">alt_route</mat-icon>
          <mat-card-title>Umweg-Check</mat-card-title>
          <mat-card-subtitle>Lohnt sich der Umweg?</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <p>Berechne ob der Umweg zum günstigeren Laden wirtschaftlich sinnvoll ist.</p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button color="primary" routerLink="/detour">Öffnen</button>
        </mat-card-actions>
      </mat-card>

      <mat-card class="feature-card" routerLink="/route">
        <mat-card-header>
          <mat-icon mat-card-avatar class="card-icon">route</mat-icon>
          <mat-card-title>Routen-Optimierer</mat-card-title>
          <mat-card-subtitle>Bester Laden finden</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <p>Finde den optimalen Laden unter Berücksichtigung von Preis und Fahrtkosten.</p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button color="primary" routerLink="/route">Öffnen</button>
        </mat-card-actions>
      </mat-card>

      <mat-card class="feature-card" routerLink="/prices">
        <mat-card-header>
          <mat-icon mat-card-avatar class="card-icon">euro</mat-icon>
          <mat-card-title>Preise</mat-card-title>
          <mat-card-subtitle>Aktuelle Marktpreise</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <p>Österreichische Supermarktpreise im Überblick.</p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button color="primary" routerLink="/prices">Öffnen</button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    h1 { margin: 0 0 4px; }
    .subtitle { color: rgba(0,0,0,.6); margin-bottom: 24px; }
    .status-bar { margin-bottom: 24px; }
    .status-card mat-card-content {
      display: flex; align-items: center; gap: 8px; padding: 12px 0 0;
    }
    .ok { color: #4caf50; }
    .err { color: #f44336; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
    .feature-card { cursor: pointer; transition: box-shadow .2s; }
    .feature-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.15); }
    .card-icon { font-size: 28px; width: 40px; height: 40px;
      display: flex; align-items: center; justify-content: center;
      background: #e3f2fd; border-radius: 50%; color: #1565c0; }
  `],
})
export class DashboardComponent implements OnInit {
  private readonly http = inject(HttpClient);
  readonly healthOk = signal(false);
  readonly healthLoading = signal(true);

  ngOnInit(): void {
    this.http.get<{ status: string }>(`${environment.apiUrl}/health`).subscribe({
      next: (res) => {
        this.healthOk.set(res.status === 'ok');
        this.healthLoading.set(false);
      },
      error: () => {
        this.healthOk.set(false);
        this.healthLoading.set(false);
      },
    });
  }
}
