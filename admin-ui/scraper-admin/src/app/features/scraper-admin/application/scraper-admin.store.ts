import { Injectable, computed, effect, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ScraperAdminApiService } from '../../../core/api/scraper-admin-api.service';
import { type CatalogItem, type ReviewItem, type ScrapedOffer, type ScraperConfig, type ScraperJob } from '../../../core/models/scraper-admin.models';

@Injectable({ providedIn: 'root' })
export class ScraperAdminStore {
  private readonly pollMs = 5000;
  private timer: ReturnType<typeof setInterval> | null = null;

  readonly loading = signal(false);
  readonly busy = signal<string | null>(null);
  readonly notice = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  readonly config = signal<ScraperConfig | null>(null);
  readonly recommendation = signal<Record<string, unknown> | null>(null);
  readonly jobs = signal<ScraperJob[]>([]);
  readonly offers = signal<ScrapedOffer[]>([]);
  readonly reviews = signal<ReviewItem[]>([]);
  readonly catalog = signal<CatalogItem[]>([]);

  readonly offerFilter = signal<'all' | 'true' | 'false'>('all');
  readonly offerPage = signal(1);
  readonly offerPageSize = signal(25);
  readonly reviewFilter = signal<'pending' | 'resolved' | 'all'>('pending');
  readonly reviewPage = signal(1);
  readonly reviewPageSize = signal(25);

  readonly running = computed(() => this.jobs().some((job) => job.status === 'running'));
  readonly pagedOffers = computed(() => {
    const page = this.offerPage();
    const size = this.offerPageSize();
    const start = (page - 1) * size;
    return this.offers().slice(start, start + size);
  });
  readonly pagedReviews = computed(() => {
    const page = this.reviewPage();
    const size = this.reviewPageSize();
    const start = (page - 1) * size;
    return this.reviews().slice(start, start + size);
  });
  readonly canOfferPrev = computed(() => this.offerPage() > 1);
  readonly canOfferNext = computed(() => this.offerPage() * this.offerPageSize() < this.offers().length);
  readonly canReviewPrev = computed(() => this.reviewPage() > 1);
  readonly canReviewNext = computed(() => this.reviewPage() * this.reviewPageSize() < this.reviews().length);

  constructor(private readonly api: ScraperAdminApiService) {
    effect(() => {
      if (this.running()) {
        this.startPolling();
      } else {
        this.stopPolling();
      }
    });
  }

  async init(): Promise<void> {
    await this.reloadAll();
  }

  async reloadAll(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const [cfg, jobs, catalog] = await Promise.all([
        firstValueFrom(this.api.getConfig()),
        firstValueFrom(this.api.getJobs()),
        firstValueFrom(this.api.listCatalog()),
      ]);
      this.config.set(cfg.config);
      this.recommendation.set(cfg.schedule_recommendation);
      this.jobs.set(jobs.items);
      this.catalog.set(catalog.items);
      await Promise.all([this.reloadOffers(), this.reloadReviews()]);
    } catch (err) {
      this.error.set(this.toError(err));
    } finally {
      this.loading.set(false);
    }
  }

  async startJob(storesCsv: string, simulate: boolean): Promise<void> {
    await this.withAction('start-job', async () => {
      const stores = storesCsv
        .split(',')
        .map((value) => value.trim())
        .filter((value) => value.length > 0);
      await firstValueFrom(this.api.startJob({ stores, simulate }));
      this.notice.set('Scraper-Job gestartet.');
      const jobs = await firstValueFrom(this.api.getJobs());
      this.jobs.set(jobs.items);
    });
  }

  async updateConfig(payload: {
    enabled: boolean;
    interval_minutes: number;
    max_parallel_stores: number;
    retries: number;
  }): Promise<void> {
    await this.withAction('update-config', async () => {
      const updated = await firstValueFrom(this.api.updateConfig(payload));
      this.config.set(updated.config);
      this.notice.set('Konfiguration gespeichert.');
    });
  }

  async bootstrapPersistence(): Promise<void> {
    await this.withAction('bootstrap', async () => {
      await firstValueFrom(this.api.bootstrapPersistence());
      this.notice.set('Persistence bootstrap erfolgreich.');
    });
  }

  async createCatalog(payload: {
    name: string;
    brand?: string | null;
    serial_number?: string | null;
    package_quantity?: number | null;
    package_unit?: string | null;
    category?: string | null;
  }): Promise<void> {
    await this.withAction('create-catalog', async () => {
      await firstValueFrom(this.api.createCatalog(payload));
      const data = await firstValueFrom(this.api.listCatalog());
      this.catalog.set(data.items);
      this.notice.set('Katalog-Artikel erstellt.');
    });
  }

  async deleteCatalog(productId: string): Promise<void> {
    await this.withAction('delete-catalog', async () => {
      await firstValueFrom(this.api.deleteCatalog(productId));
      const data = await firstValueFrom(this.api.listCatalog());
      this.catalog.set(data.items);
      this.notice.set('Katalog-Artikel gelöscht.');
    });
  }

  async updateOffer(
    offerId: string,
    payload: Partial<{
      price_eur: number;
      valid_from: string;
      valid_to: string;
      price_type: string;
      canonical_product_id: string;
      needs_review: boolean;
      review_reason: string;
    }>,
  ): Promise<void> {
    await this.withAction('update-offer', async () => {
      await firstValueFrom(this.api.updateOffer(offerId, payload));
      await this.reloadOffers();
      this.notice.set('Offer aktualisiert.');
    });
  }

  async deleteOffer(offerId: string): Promise<void> {
    await this.withAction('delete-offer', async () => {
      await firstValueFrom(this.api.deleteOffer(offerId));
      await this.reloadOffers();
      this.notice.set('Offer gelöscht.');
    });
  }

  async resolveReview(reviewId: string, canonicalProductId: string, reviewerNote?: string): Promise<void> {
    await this.withAction('resolve-review', async () => {
      await firstValueFrom(
        this.api.resolveReview(reviewId, {
          canonical_product_id: canonicalProductId,
          reviewer_note: reviewerNote,
        }),
      );
      await Promise.all([this.reloadReviews(), this.reloadOffers()]);
      this.notice.set('Review aufgelöst.');
    });
  }

  setOfferFilter(filter: 'all' | 'true' | 'false'): void {
    this.offerFilter.set(filter);
    this.offerPage.set(1);
    void this.reloadOffers();
  }

  setReviewFilter(filter: 'pending' | 'resolved' | 'all'): void {
    this.reviewFilter.set(filter);
    this.reviewPage.set(1);
    void this.reloadReviews();
  }

  setOfferPageSize(value: number): void {
    this.offerPageSize.set(Math.max(1, Math.min(200, value)));
    this.offerPage.set(1);
  }

  setReviewPageSize(value: number): void {
    this.reviewPageSize.set(Math.max(1, Math.min(200, value)));
    this.reviewPage.set(1);
  }

  nextOfferPage(): void {
    if (this.canOfferNext()) {
      this.offerPage.update((page) => page + 1);
    }
  }

  prevOfferPage(): void {
    if (this.canOfferPrev()) {
      this.offerPage.update((page) => page - 1);
    }
  }

  nextReviewPage(): void {
    if (this.canReviewNext()) {
      this.reviewPage.update((page) => page + 1);
    }
  }

  prevReviewPage(): void {
    if (this.canReviewPrev()) {
      this.reviewPage.update((page) => page - 1);
    }
  }

  private async reloadOffers(): Promise<void> {
    const data = await firstValueFrom(
      this.api.listOffers({
        needsReview: this.offerFilter(),
        limit: 2000,
      }),
    );
    this.offers.set(data.items);
    const maxPage = Math.max(1, Math.ceil(data.items.length / this.offerPageSize()));
    if (this.offerPage() > maxPage) this.offerPage.set(maxPage);
  }

  private async reloadReviews(): Promise<void> {
    const data = await firstValueFrom(
      this.api.listReviews({
        status: this.reviewFilter(),
        limit: 2000,
      }),
    );
    this.reviews.set(data.items);
    const maxPage = Math.max(1, Math.ceil(data.items.length / this.reviewPageSize()));
    if (this.reviewPage() > maxPage) this.reviewPage.set(maxPage);
  }

  private async withAction(name: string, action: () => Promise<void>): Promise<void> {
    this.busy.set(name);
    this.error.set(null);
    try {
      await action();
    } catch (err) {
      this.error.set(this.toError(err));
    } finally {
      this.busy.set(null);
    }
  }

  private startPolling(): void {
    if (this.timer) return;
    this.timer = setInterval(async () => {
      try {
        const jobs = await firstValueFrom(this.api.getJobs());
        this.jobs.set(jobs.items);
        await Promise.all([this.reloadOffers(), this.reloadReviews()]);
      } catch {
        // polling should not hard fail the UI
      }
    }, this.pollMs);
  }

  private stopPolling(): void {
    if (!this.timer) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  private toError(err: unknown): string {
    if (err && typeof err === 'object' && 'message' in err) {
      const maybeMessage = (err as { message?: string }).message;
      if (maybeMessage) return maybeMessage;
    }
    return 'Unbekannter Fehler';
  }
}
