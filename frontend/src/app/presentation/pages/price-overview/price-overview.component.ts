import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';

import { PriceStore } from '../../../application/stores/price.store';

@Component({
  selector: 'app-price-overview',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatProgressBarModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
  ],
  template: `
    <h1>Preisübersicht</h1>
    <p class="subtitle">Aktuelle österreichische Supermarktpreise.</p>

    <div class="actions">
      <button mat-raised-button color="primary" (click)="store.loadPrices(undefined)"
        [disabled]="store.loading()">
        <mat-icon>refresh</mat-icon> Preise laden
      </button>
      <mat-chip-set>
        <mat-chip>{{ store.recordCount() }} Einträge</mat-chip>
      </mat-chip-set>
    </div>

    @if (store.loading()) {
      <mat-progress-bar mode="indeterminate"></mat-progress-bar>
    }

    @if (store.error()) {
      <mat-card appearance="outlined" class="error-card">
        <mat-card-content>
          <mat-icon>error</mat-icon>
          <span>{{ store.error() }}</span>
        </mat-card-content>
      </mat-card>
    }

    @if (store.records().length > 0) {
      <mat-card appearance="outlined" class="table-card">
        <table mat-table [dataSource]="store.records()">
          <ng-container matColumnDef="store_id">
            <th mat-header-cell *matHeaderCellDef>Laden</th>
            <td mat-cell *matCellDef="let r">{{ r.store_id }}</td>
          </ng-container>
          <ng-container matColumnDef="product_key">
            <th mat-header-cell *matHeaderCellDef>Produkt</th>
            <td mat-cell *matCellDef="let r">{{ r.product_key }}</td>
          </ng-container>
          <ng-container matColumnDef="price_eur">
            <th mat-header-cell *matHeaderCellDef>Preis (€)</th>
            <td mat-cell *matCellDef="let r" class="price">€{{ r.price_eur.toFixed(2) }}</td>
          </ng-container>
          <ng-container matColumnDef="date">
            <th mat-header-cell *matHeaderCellDef>Datum</th>
            <td mat-cell *matCellDef="let r">{{ r.date }}</td>
          </ng-container>
          <ng-container matColumnDef="source">
            <th mat-header-cell *matHeaderCellDef>Quelle</th>
            <td mat-cell *matCellDef="let r">
              <mat-chip>{{ r.source }}</mat-chip>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
        </table>
      </mat-card>

      @if (store.cheapestByProduct().length > 0) {
        <mat-card appearance="outlined" class="cheapest-card">
          <mat-card-header>
            <mat-icon mat-card-avatar class="best-icon">emoji_events</mat-icon>
            <mat-card-title>Günstigster Anbieter je Produkt</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            @for (item of store.cheapestByProduct(); track item.product_key) {
              <div class="cheapest-row">
                <span class="product">{{ item.product_key }}</span>
                <span class="store">{{ item.store_id }}</span>
                <span class="price">€{{ item.price_eur.toFixed(2) }}</span>
              </div>
            }
          </mat-card-content>
        </mat-card>
      }
    }
  `,
  styles: [`
    h1 { margin: 0 0 4px; }
    .subtitle { color: rgba(0,0,0,.6); margin-bottom: 24px; }
    .actions { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
    .error-card { margin-bottom: 16px; border-left: 4px solid #f44336; }
    .error-card mat-card-content { display: flex; align-items: center; gap: 8px; color: #f44336; padding-top: 12px; }
    .table-card { margin-bottom: 16px; overflow: auto; }
    table { width: 100%; }
    .price { font-weight: 600; color: #1565c0; }
    .cheapest-card { margin-top: 16px; border-left: 4px solid #ffc107; }
    .best-icon { color: #ffc107; background: #fff8e1; border-radius: 50%;
      width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
    .cheapest-row {
      display: flex; gap: 16px; padding: 8px 0;
      border-bottom: 1px solid rgba(0,0,0,.06);
    }
    .cheapest-row .product { font-weight: 500; min-width: 140px; }
    .cheapest-row .store { color: rgba(0,0,0,.6); min-width: 120px; }
    .cheapest-row .price { font-weight: 600; color: #4caf50; }
  `],
})
export class PriceOverviewComponent implements OnInit {
  readonly store = inject(PriceStore);
  readonly displayedColumns = ['store_id', 'product_key', 'price_eur', 'date', 'source'];

  ngOnInit(): void {
    this.store.loadPrices(undefined);
  }
}
