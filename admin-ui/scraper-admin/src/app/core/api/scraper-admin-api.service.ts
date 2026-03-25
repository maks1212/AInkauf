import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CatalogItem,
  ReviewItem,
  ScrapedOffer,
  ScraperConfig,
  ScraperJob,
  ScheduleRecommendation
} from '../models/scraper-admin.models';

@Injectable({ providedIn: 'root' })
export class ScraperAdminApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  getConfig(): Observable<{ config: ScraperConfig; schedule_recommendation: ScheduleRecommendation }> {
    return this.http.get<{ config: ScraperConfig; schedule_recommendation: ScheduleRecommendation }>(
      `${this.baseUrl}/admin/scraper/config`
    );
  }

  updateConfig(payload: Partial<ScraperConfig>): Observable<{ config: ScraperConfig }> {
    return this.http.patch<{ config: ScraperConfig }>(`${this.baseUrl}/admin/scraper/config`, payload);
  }

  listJobs(limit = 40): Observable<{ running: boolean; items: ScraperJob[] }> {
    const params = new HttpParams().set('limit', String(limit));
    return this.http.get<{ running: boolean; items: ScraperJob[] }>(`${this.baseUrl}/admin/scraper/jobs`, {
      params
    });
  }

  startJob(payload: { stores?: string[]; simulate?: boolean }): Observable<{ job: ScraperJob }> {
    return this.http.post<{ job: ScraperJob }>(`${this.baseUrl}/admin/scraper/jobs/start`, payload);
  }

  bootstrapPersistence(): Observable<{ bootstrapped: boolean }> {
    return this.http.post<{ bootstrapped: boolean }>(`${this.baseUrl}/admin/scraper/bootstrap`, {});
  }

  listCatalog(): Observable<{ items: CatalogItem[] }> {
    return this.http.get<{ items: CatalogItem[] }>(`${this.baseUrl}/admin/scraper/catalog`);
  }

  createCatalog(payload: {
    name: string;
    brand?: string | null;
    serial_number?: string | null;
    package_quantity?: number | null;
    package_unit?: string | null;
    category?: string | null;
  }): Observable<{ item: CatalogItem }> {
    return this.http.post<{ item: CatalogItem }>(`${this.baseUrl}/admin/scraper/catalog`, payload);
  }

  deleteCatalog(productId: string): Observable<{ deleted: boolean }> {
    return this.http.delete<{ deleted: boolean }>(`${this.baseUrl}/admin/scraper/catalog/${productId}`);
  }

  listOffers(params: { needsReview?: 'all' | 'true' | 'false'; limit?: number }): Observable<{ items: ScrapedOffer[] }> {
    let httpParams = new HttpParams().set('limit', String(params.limit ?? 2000));
    if (params.needsReview === 'true') {
      httpParams = httpParams.set('needs_review', 'true');
    } else if (params.needsReview === 'false') {
      httpParams = httpParams.set('needs_review', 'false');
    }
    return this.http.get<{ items: ScrapedOffer[] }>(`${this.baseUrl}/admin/scraper/offers`, {
      params: httpParams
    });
  }

  updateOffer(offerId: string, payload: Partial<ScrapedOffer>): Observable<{ item: ScrapedOffer }> {
    return this.http.patch<{ item: ScrapedOffer }>(`${this.baseUrl}/admin/scraper/offers/${offerId}`, payload);
  }

  deleteOffer(offerId: string): Observable<{ deleted: boolean }> {
    return this.http.delete<{ deleted: boolean }>(`${this.baseUrl}/admin/scraper/offers/${offerId}`);
  }

  listReviews(params: { status: 'pending' | 'resolved' | 'all'; limit?: number }): Observable<{ items: ReviewItem[] }> {
    const httpParams = new HttpParams()
      .set('status', params.status)
      .set('limit', String(params.limit ?? 2000));
    return this.http.get<{ items: ReviewItem[] }>(`${this.baseUrl}/admin/scraper/reviews`, {
      params: httpParams
    });
  }

  resolveReview(
    reviewId: string,
    payload: { canonical_product_id: string; reviewer_note?: string | null }
  ): Observable<{ item: ReviewItem }> {
    return this.http.post<{ item: ReviewItem }>(
      `${this.baseUrl}/admin/scraper/reviews/${reviewId}/resolve`,
      payload
    );
  }
}
