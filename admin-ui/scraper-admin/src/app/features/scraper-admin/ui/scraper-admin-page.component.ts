import { CommonModule } from '@angular/common';
import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ScraperAdminStore } from '../application/scraper-admin.store';

@Component({
  selector: 'app-scraper-admin-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scraper-admin-page.component.html',
})
export class ScraperAdminPageComponent {
  protected readonly store = inject(ScraperAdminStore);

  protected readonly storesCsv = signal('billa,spar,lidl');
  protected readonly simulate = signal(false);

  protected readonly cfgEnabled = signal(false);
  protected readonly cfgInterval = signal(180);
  protected readonly cfgWorkers = signal(4);
  protected readonly cfgRetries = signal(2);

  protected readonly catalogName = signal('');
  protected readonly catalogBrand = signal('');
  protected readonly catalogSerial = signal('');
  protected readonly catalogQty = signal('');
  protected readonly catalogUnit = signal('');
  protected readonly catalogCategory = signal('');

  protected readonly selectedCatalogId = signal('');
  protected readonly reviewNote = signal('');

  constructor() {
    void this.store.init();
    effect(() => {
      const cfg = this.store.config();
      if (!cfg) return;
      this.cfgEnabled.set(cfg.enabled);
      this.cfgInterval.set(cfg.interval_minutes);
      this.cfgWorkers.set(cfg.max_parallel_stores);
      this.cfgRetries.set(cfg.retries);
    });
  }

  protected async startJob(): Promise<void> {
    await this.store.startJob(this.storesCsv(), this.simulate());
  }

  protected async saveConfig(): Promise<void> {
    await this.store.updateConfig({
      enabled: this.cfgEnabled(),
      interval_minutes: this.cfgInterval(),
      max_parallel_stores: this.cfgWorkers(),
      retries: this.cfgRetries(),
    });
  }

  protected async createCatalogItem(): Promise<void> {
    await this.store.createCatalog({
      name: this.catalogName().trim(),
      brand: this.catalogBrand().trim() || undefined,
      serial_number: this.catalogSerial().trim() || undefined,
      package_quantity: this.catalogQty().trim() ? Number(this.catalogQty()) : undefined,
      package_unit: this.catalogUnit().trim() || undefined,
      category: this.catalogCategory().trim() || undefined,
    });
    this.catalogName.set('');
    this.catalogBrand.set('');
    this.catalogSerial.set('');
    this.catalogQty.set('');
    this.catalogUnit.set('');
    this.catalogCategory.set('');
  }

  protected async deleteCatalogItem(productId: string): Promise<void> {
    await this.store.deleteCatalog(productId);
  }

  protected async toggleOfferReview(offerId: string, current: boolean): Promise<void> {
    await this.store.updateOffer(offerId, { needs_review: !current });
  }

  protected async deleteOffer(offerId: string): Promise<void> {
    await this.store.deleteOffer(offerId);
  }

  protected async resolveReview(reviewId: string): Promise<void> {
    const canonical = this.selectedCatalogId().trim();
    if (!canonical) {
      this.store.error.set('Bitte zuerst ein Canonical Product waehlen.');
      return;
    }
    await this.store.resolveReview(reviewId, canonical, this.reviewNote().trim() || undefined);
    this.reviewNote.set('');
  }
}
