import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from '@auth0/auth0-angular';

import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
  ],
  template: `
    <mat-toolbar color="primary" class="toolbar">
      <button mat-icon-button (click)="sidenavOpen.set(!sidenavOpen())">
        <mat-icon>menu</mat-icon>
      </button>
      <span class="brand">AInkauf</span>
      <span class="spacer"></span>
      @if (authConfigured) {
        @if (auth.isAuthenticated$ | async) {
          <span class="user-name">{{ (auth.user$ | async)?.name }}</span>
          <button mat-button (click)="auth.logout({ logoutParams: { returnTo: origin } })">
            Abmelden
          </button>
        } @else {
          <button mat-raised-button (click)="auth.loginWithRedirect()">
            Anmelden
          </button>
        }
      } @else {
        <span class="dev-badge">Dev Mode</span>
      }
    </mat-toolbar>

    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav [opened]="sidenavOpen()" mode="side" class="sidenav">
        <mat-nav-list>
          <a mat-list-item routerLink="/dashboard" routerLinkActive="active">
            <mat-icon matListItemIcon>dashboard</mat-icon>
            <span matListItemTitle>Dashboard</span>
          </a>
          <a mat-list-item routerLink="/nlp" routerLinkActive="active">
            <mat-icon matListItemIcon>text_fields</mat-icon>
            <span matListItemTitle>NLP Parser</span>
          </a>
          <a mat-list-item routerLink="/detour" routerLinkActive="active">
            <mat-icon matListItemIcon>alt_route</mat-icon>
            <span matListItemTitle>Umweg-Check</span>
          </a>
          <a mat-list-item routerLink="/route" routerLinkActive="active">
            <mat-icon matListItemIcon>route</mat-icon>
            <span matListItemTitle>Routen-Optimierer</span>
          </a>
          <a mat-list-item routerLink="/prices" routerLinkActive="active">
            <mat-icon matListItemIcon>euro</mat-icon>
            <span matListItemTitle>Preise</span>
          </a>
        </mat-nav-list>
      </mat-sidenav>

      <mat-sidenav-content class="content">
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    :host { display: flex; flex-direction: column; height: 100vh; }
    .toolbar { position: sticky; top: 0; z-index: 100; }
    .brand { font-weight: 700; margin-left: 8px; font-size: 20px; }
    .spacer { flex: 1; }
    .user-name { margin-right: 12px; font-size: 14px; opacity: 0.9; }
    .dev-badge {
      background: rgba(255,255,255,.2); border-radius: 4px;
      padding: 4px 10px; font-size: 12px; font-weight: 500;
    }
    .sidenav-container { flex: 1; }
    .sidenav { width: 220px; }
    .content { padding: 24px; }
    .active { background: rgba(0,0,0,.04); }
  `],
})
export class ShellComponent {
  readonly auth = inject(AuthService);
  readonly sidenavOpen = signal(true);
  readonly authConfigured =
    environment.auth0.domain !== 'YOUR_AUTH0_DOMAIN.auth0.com' &&
    environment.auth0.clientId !== 'YOUR_AUTH0_CLIENT_ID';
  readonly origin = typeof window !== 'undefined' ? window.location.origin : '';
}
