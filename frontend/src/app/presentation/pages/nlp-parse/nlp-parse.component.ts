import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';

import { NlpStore } from '../../../application/stores/nlp.store';

@Component({
  selector: 'app-nlp-parse',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressBarModule,
    MatIconModule,
    MatChipsModule,
  ],
  template: `
    <h1>NLP Artikel-Parser</h1>
    <p class="subtitle">Gib einen Einkaufsartikel im Freitext ein, z.B. „3kg Äpfel" oder „2 l Milch".</p>

    <mat-card appearance="outlined" class="input-card">
      <mat-card-content>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Artikel eingeben</mat-label>
          <input matInput
            [(ngModel)]="inputText"
            placeholder="z.B. 3kg Äpfel"
            (keyup.enter)="parse()" />
          <mat-icon matSuffix>text_fields</mat-icon>
        </mat-form-field>

        <button mat-raised-button color="primary"
          [disabled]="!inputText || store.loading()"
          (click)="parse()">
          Parsen
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

    @if (store.hasResult()) {
      <mat-card appearance="outlined" class="result-card">
        <mat-card-header>
          <mat-icon mat-card-avatar class="result-icon">check_circle</mat-icon>
          <mat-card-title>Ergebnis</mat-card-title>
          <mat-card-subtitle>{{ store.formattedResult() }}</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <div class="chips">
            <mat-chip-set>
              <mat-chip highlighted>Menge: {{ store.result()!.quantity }}</mat-chip>
              <mat-chip highlighted>Einheit: {{ store.result()!.unit }}</mat-chip>
              <mat-chip highlighted>Produkt: {{ store.result()!.product_name }}</mat-chip>
            </mat-chip-set>
          </div>
        </mat-card-content>
      </mat-card>
    }

    <mat-card appearance="outlined" class="examples-card">
      <mat-card-header>
        <mat-card-title>Beispiele</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <div class="example-chips">
          @for (example of examples; track example) {
            <button mat-stroked-button (click)="inputText = example; parse()">
              {{ example }}
            </button>
          }
        </div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    h1 { margin: 0 0 4px; }
    .subtitle { color: rgba(0,0,0,.6); margin-bottom: 24px; }
    .input-card { margin-bottom: 16px; }
    .input-card mat-card-content { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
    .full-width { flex: 1; min-width: 260px; }
    .progress { margin-top: 8px; }
    .error-card { margin-bottom: 16px; border-left: 4px solid #f44336; }
    .error-card mat-card-content { display: flex; align-items: center; gap: 8px; color: #f44336; padding-top: 12px; }
    .result-card { margin-bottom: 16px; border-left: 4px solid #4caf50; }
    .result-icon { color: #4caf50; background: #e8f5e9; border-radius: 50%;
      width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
    .chips { margin-top: 12px; }
    .examples-card { margin-top: 16px; }
    .example-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  `],
})
export class NlpParseComponent {
  readonly store = inject(NlpStore);
  inputText = '';
  readonly examples = ['3kg Äpfel', '2 l Milch', '500g Brot', '1 stk Butter', '250ml Sahne'];

  parse(): void {
    if (this.inputText) {
      this.store.parseItem(this.inputText);
    }
  }
}
