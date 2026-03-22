import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';

import { DetourStore } from '../../../application/stores/detour.store';
import { DetourCheckRequest } from '../../../core/models/detour-check.model';
import { TransportMode, FuelType } from '../../../core/models/user-context.model';

@Component({
  selector: 'app-detour-check',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressBarModule,
    MatIconModule,
    MatDividerModule,
  ],
  template: `
    <h1>Umweg-Check</h1>
    <p class="subtitle">Lohnt sich der Umweg zum günstigeren Laden?</p>

    <mat-card appearance="outlined" class="form-card">
      <mat-card-header>
        <mat-card-title>Preise & Strecke</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <div class="form-row">
          <mat-form-field appearance="outline">
            <mat-label>Preis Basisladen (€)</mat-label>
            <input matInput type="number" [(ngModel)]="form.baseTotal" min="0" step="0.01" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Preis Alternativladen (€)</mat-label>
            <input matInput type="number" [(ngModel)]="form.candidateTotal" min="0" step="0.01" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Umweg-Distanz (km)</mat-label>
            <input matInput type="number" [(ngModel)]="form.detourKm" min="0" step="0.5" />
          </mat-form-field>
        </div>

        <mat-divider></mat-divider>

        <h3>Transport</h3>
        <div class="form-row">
          <mat-form-field appearance="outline">
            <mat-label>Transportmittel</mat-label>
            <mat-select [(ngModel)]="form.transportMode">
              <mat-option value="car">Auto</mat-option>
              <mat-option value="bike">Fahrrad</mat-option>
              <mat-option value="foot">Zu Fuß</mat-option>
              <mat-option value="transit">Öffis</mat-option>
            </mat-select>
          </mat-form-field>

          @if (form.transportMode === 'car') {
            <mat-form-field appearance="outline">
              <mat-label>Verbrauch (pro 100km)</mat-label>
              <input matInput type="number" [(ngModel)]="form.consumption" min="0" step="0.1" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Antriebsart</mat-label>
              <mat-select [(ngModel)]="form.fuelType">
                <mat-option value="benzin">Benzin</mat-option>
                <mat-option value="diesel">Diesel</mat-option>
                <mat-option value="autogas">Autogas</mat-option>
                <mat-option value="strom">Strom</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Energiepreis (€/Einheit)</mat-label>
              <input matInput type="number" [(ngModel)]="form.energyPrice" min="0" step="0.01" />
            </mat-form-field>
          }
        </div>

        <button mat-raised-button color="primary"
          [disabled]="store.loading()"
          (click)="submit()">
          Berechnen
        </button>

        @if (store.loading()) {
          <mat-progress-bar mode="indeterminate" class="progress"></mat-progress-bar>
        }
      </mat-card-content>
    </mat-card>

    @if (store.error()) {
      <mat-card appearance="outlined" class="error-card">
        <mat-card-content>
          <mat-icon>error</mat-icon>
          <span>{{ store.error() }}</span>
        </mat-card-content>
      </mat-card>
    }

    @if (store.result()) {
      <mat-card appearance="outlined" class="result-card"
        [class.worth-it]="store.result()!.is_worth_it"
        [class.not-worth-it]="!store.result()!.is_worth_it">
        <mat-card-header>
          <mat-icon mat-card-avatar class="result-icon">
            {{ store.result()!.is_worth_it ? 'thumb_up' : 'thumb_down' }}
          </mat-icon>
          <mat-card-title>
            {{ store.result()!.is_worth_it ? 'Umweg lohnt sich!' : 'Umweg lohnt sich nicht' }}
          </mat-card-title>
          <mat-card-subtitle>{{ store.result()!.explanation }}</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <div class="metrics">
            <div class="metric">
              <span class="label">Brutto-Ersparnis</span>
              <span class="value">€{{ store.result()!.gross_savings_eur.toFixed(2) }}</span>
            </div>
            <div class="metric">
              <span class="label">Mobilitätskosten</span>
              <span class="value">€{{ store.result()!.mobility_cost_eur.toFixed(2) }}</span>
            </div>
            <div class="metric highlight">
              <span class="label">Netto-Ersparnis</span>
              <span class="value" [class.positive]="store.result()!.net_savings_eur >= 0"
                [class.negative]="store.result()!.net_savings_eur < 0">
                €{{ store.result()!.net_savings_eur.toFixed(2) }}
              </span>
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: [`
    h1 { margin: 0 0 4px; }
    .subtitle { color: rgba(0,0,0,.6); margin-bottom: 24px; }
    .form-card { margin-bottom: 16px; }
    .form-card mat-card-content { padding-top: 16px; }
    .form-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    h3 { margin: 12px 0 8px; font-weight: 500; }
    .progress { margin-top: 12px; }
    .error-card { margin-bottom: 16px; border-left: 4px solid #f44336; }
    .error-card mat-card-content { display: flex; align-items: center; gap: 8px; color: #f44336; padding-top: 12px; }
    .result-card { margin-top: 16px; }
    .worth-it { border-left: 4px solid #4caf50; }
    .not-worth-it { border-left: 4px solid #ff9800; }
    .result-icon {
      width: 40px; height: 40px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
    }
    .worth-it .result-icon { color: #4caf50; background: #e8f5e9; }
    .not-worth-it .result-icon { color: #ff9800; background: #fff3e0; }
    .metrics { display: flex; gap: 24px; flex-wrap: wrap; margin-top: 16px; }
    .metric { display: flex; flex-direction: column; }
    .metric .label { font-size: 12px; color: rgba(0,0,0,.6); text-transform: uppercase; }
    .metric .value { font-size: 22px; font-weight: 600; }
    .highlight .value { font-size: 28px; }
    .positive { color: #4caf50; }
    .negative { color: #f44336; }
  `],
})
export class DetourCheckComponent {
  readonly store = inject(DetourStore);

  form = {
    baseTotal: 42.90,
    candidateTotal: 41.99,
    detourKm: 5,
    transportMode: 'car' as TransportMode,
    fuelType: 'benzin' as FuelType,
    consumption: 6.5,
    energyPrice: 1.70,
  };

  submit(): void {
    const req: DetourCheckRequest = {
      base_store_total_eur: this.form.baseTotal,
      candidate_store_total_eur: this.form.candidateTotal,
      detour_distance_km: this.form.detourKm,
      energy_price_eur_per_unit:
        this.form.transportMode === 'car' ? this.form.energyPrice : undefined,
      user: {
        location: { lat: 48.2082, lng: 16.3738 },
        transport_mode: this.form.transportMode,
        vehicle_consumption_per_100km:
          this.form.transportMode === 'car' ? this.form.consumption : undefined,
        fuel_type: this.form.transportMode === 'car' ? this.form.fuelType : undefined,
      },
    };
    this.store.checkDetour(req);
  }
}
