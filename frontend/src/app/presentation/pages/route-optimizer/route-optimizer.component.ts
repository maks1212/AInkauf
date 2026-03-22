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
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';

import { RouteStore } from '../../../application/stores/route.store';
import { RouteRequest, StoreBasket, ShoppingListItem } from '../../../core/models/route.model';
import { TransportMode, FuelType } from '../../../core/models/user-context.model';

@Component({
  selector: 'app-route-optimizer',
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
    MatTableModule,
    MatChipsModule,
  ],
  template: `
    <h1>Routen-Optimierer</h1>
    <p class="subtitle">Finde den besten Laden unter Berücksichtigung von Preis und Fahrtkosten.</p>

    <mat-card appearance="outlined" class="form-card">
      <mat-card-header><mat-card-title>Transport</mat-card-title></mat-card-header>
      <mat-card-content>
        <div class="form-row">
          <mat-form-field appearance="outline">
            <mat-label>Transportmittel</mat-label>
            <mat-select [(ngModel)]="transportMode">
              <mat-option value="car">Auto</mat-option>
              <mat-option value="bike">Fahrrad</mat-option>
              <mat-option value="foot">Zu Fuß</mat-option>
              <mat-option value="transit">Öffis</mat-option>
            </mat-select>
          </mat-form-field>
          @if (transportMode === 'car') {
            <mat-form-field appearance="outline">
              <mat-label>Verbrauch (pro 100km)</mat-label>
              <input matInput type="number" [(ngModel)]="consumption" min="0" step="0.1" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Antriebsart</mat-label>
              <mat-select [(ngModel)]="fuelType">
                <mat-option value="benzin">Benzin</mat-option>
                <mat-option value="diesel">Diesel</mat-option>
                <mat-option value="autogas">Autogas</mat-option>
                <mat-option value="strom">Strom</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Energiepreis (€/Einheit)</mat-label>
              <input matInput type="number" [(ngModel)]="energyPrice" min="0" step="0.01" />
            </mat-form-field>
          }
        </div>
      </mat-card-content>
    </mat-card>

    <mat-card appearance="outlined" class="form-card">
      <mat-card-header>
        <mat-card-title>Läden ({{ stores.length }})</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        @for (s of stores; track idx; let idx = $index) {
          <div class="store-row">
            <mat-form-field appearance="outline" class="sm">
              <mat-label>Kette</mat-label>
              <input matInput [(ngModel)]="s.chain" />
            </mat-form-field>
            <mat-form-field appearance="outline" class="sm">
              <mat-label>Lat</mat-label>
              <input matInput type="number" [(ngModel)]="s.location.lat" step="0.001" />
            </mat-form-field>
            <mat-form-field appearance="outline" class="sm">
              <mat-label>Lng</mat-label>
              <input matInput type="number" [(ngModel)]="s.location.lng" step="0.001" />
            </mat-form-field>
            <mat-form-field appearance="outline" class="sm">
              <mat-label>Warenkorb (€)</mat-label>
              <input matInput type="number" [(ngModel)]="s.basket_total_eur" min="0" step="0.01" />
            </mat-form-field>
            <button mat-icon-button color="warn" (click)="removeStore(idx)"
              [disabled]="stores.length <= 2">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        }
        <button mat-stroked-button (click)="addStore()">
          <mat-icon>add</mat-icon> Laden hinzufügen
        </button>
      </mat-card-content>
    </mat-card>

    <button mat-raised-button color="primary"
      [disabled]="store.loading() || stores.length < 2"
      (click)="submit()" class="submit-btn">
      Route berechnen
    </button>

    @if (store.loading()) {
      <mat-progress-bar mode="indeterminate" class="progress"></mat-progress-bar>
    }

    @if (store.error()) {
      <mat-card appearance="outlined" class="error-card">
        <mat-card-content>
          <mat-icon>error</mat-icon>
          <span>{{ store.error() }}</span>
        </mat-card-content>
      </mat-card>
    }

    @if (store.result()) {
      <mat-card appearance="outlined" class="result-card">
        <mat-card-header>
          <mat-icon mat-card-avatar class="rec-icon">recommend</mat-icon>
          <mat-card-title>Empfehlung: {{ store.result()!.recommended_store_id }}</mat-card-title>
          <mat-card-subtitle>
            Geschätzte Gesamtkosten: €{{ store.result()!.estimated_total_eur.toFixed(2) }}
          </mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <table mat-table [dataSource]="store.result()!.decisions" class="decisions-table">
            <ng-container matColumnDef="store_id">
              <th mat-header-cell *matHeaderCellDef>Laden</th>
              <td mat-cell *matCellDef="let d">
                {{ d.store_id }}
                @if (d.store_id === store.result()!.recommended_store_id) {
                  <mat-icon class="rec-badge">star</mat-icon>
                }
              </td>
            </ng-container>
            <ng-container matColumnDef="distance_km">
              <th mat-header-cell *matHeaderCellDef>Distanz</th>
              <td mat-cell *matCellDef="let d">{{ d.distance_km }} km</td>
            </ng-container>
            <ng-container matColumnDef="basket_total_eur">
              <th mat-header-cell *matHeaderCellDef>Warenkorb</th>
              <td mat-cell *matCellDef="let d">€{{ d.basket_total_eur.toFixed(2) }}</td>
            </ng-container>
            <ng-container matColumnDef="mobility_cost_eur">
              <th mat-header-cell *matHeaderCellDef>Fahrtkosten</th>
              <td mat-cell *matCellDef="let d">€{{ d.mobility_cost_eur.toFixed(2) }}</td>
            </ng-container>
            <ng-container matColumnDef="net_savings">
              <th mat-header-cell *matHeaderCellDef>Netto</th>
              <td mat-cell *matCellDef="let d"
                [class.positive]="d.net_savings_vs_baseline_eur >= 0"
                [class.negative]="d.net_savings_vs_baseline_eur < 0">
                €{{ d.net_savings_vs_baseline_eur.toFixed(2) }}
              </td>
            </ng-container>
            <ng-container matColumnDef="reason">
              <th mat-header-cell *matHeaderCellDef>Begründung</th>
              <td mat-cell *matCellDef="let d">{{ d.reason }}</td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"
              [class.recommended]="row.store_id === store.result()!.recommended_store_id">
            </tr>
          </table>
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: [`
    h1 { margin: 0 0 4px; }
    .subtitle { color: rgba(0,0,0,.6); margin-bottom: 24px; }
    .form-card { margin-bottom: 16px; }
    .form-card mat-card-content { padding-top: 16px; }
    .form-row { display: flex; gap: 16px; flex-wrap: wrap; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    .store-row { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; margin-bottom: 4px; }
    .sm { width: 140px; }
    .submit-btn { margin-top: 8px; }
    .progress { margin-top: 12px; }
    .error-card { margin-top: 16px; border-left: 4px solid #f44336; }
    .error-card mat-card-content { display: flex; align-items: center; gap: 8px; color: #f44336; padding-top: 12px; }
    .result-card { margin-top: 16px; border-left: 4px solid #1565c0; }
    .rec-icon { color: #1565c0; background: #e3f2fd; border-radius: 50%;
      width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
    .decisions-table { width: 100%; margin-top: 16px; }
    .rec-badge { color: #ffc107; font-size: 18px; vertical-align: middle; margin-left: 4px; }
    .recommended { background: #e3f2fd; }
    .positive { color: #4caf50; font-weight: 600; }
    .negative { color: #f44336; font-weight: 600; }
  `],
})
export class RouteOptimizerComponent {
  readonly store = inject(RouteStore);
  readonly displayedColumns = [
    'store_id', 'distance_km', 'basket_total_eur',
    'mobility_cost_eur', 'net_savings', 'reason',
  ];

  transportMode: TransportMode = 'car';
  fuelType: FuelType = 'benzin';
  consumption = 7.0;
  energyPrice = 1.80;

  shoppingList: ShoppingListItem[] = [
    { name: 'Äpfel', quantity: 2, unit: 'kg' },
  ];

  stores: StoreBasket[] = [
    {
      store_id: 'spar-nearby',
      chain: 'Spar',
      location: { lat: 48.2090, lng: 16.3740 },
      basket_total_eur: 30.0,
      missing_items: 0,
    },
    {
      store_id: 'hofer-far',
      chain: 'Hofer',
      location: { lat: 48.2800, lng: 16.5000 },
      basket_total_eur: 27.50,
      missing_items: 0,
    },
  ];

  addStore(): void {
    const idx = this.stores.length + 1;
    this.stores = [
      ...this.stores,
      {
        store_id: `store-${idx}`,
        chain: '',
        location: { lat: 48.2, lng: 16.37 },
        basket_total_eur: 0,
        missing_items: 0,
      },
    ];
  }

  removeStore(idx: number): void {
    this.stores = this.stores.filter((_, i) => i !== idx);
  }

  submit(): void {
    const req: RouteRequest = {
      shopping_list: this.shoppingList,
      energy_price_eur_per_unit:
        this.transportMode === 'car' ? this.energyPrice : undefined,
      user: {
        location: { lat: 48.2082, lng: 16.3738 },
        transport_mode: this.transportMode,
        vehicle_consumption_per_100km:
          this.transportMode === 'car' ? this.consumption : undefined,
        fuel_type: this.transportMode === 'car' ? this.fuelType : undefined,
      },
      stores: this.stores,
    };
    this.store.calculateRoute(req);
  }
}
