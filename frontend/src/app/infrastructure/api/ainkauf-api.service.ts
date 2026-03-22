import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AInkaufApiPort } from '../../core/ports/api.port';
import { ParseRequest, ParseResponse } from '../../core/models/parse-item.model';
import { DetourCheckRequest, DetourCheckResponse } from '../../core/models/detour-check.model';
import { RouteRequest, RouteResponse } from '../../core/models/route.model';
import { PriceResponse } from '../../core/models/price.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AInkaufApiService extends AInkaufApiPort {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  healthCheck(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(`${this.baseUrl}/health`);
  }

  parseItem(request: ParseRequest): Observable<ParseResponse> {
    return this.http.post<ParseResponse>(`${this.baseUrl}/nlp/parse-item`, request);
  }

  detourCheck(request: DetourCheckRequest): Observable<DetourCheckResponse> {
    return this.http.post<DetourCheckResponse>(
      `${this.baseUrl}/optimization/detour-worth-it`,
      request,
    );
  }

  calculateOptimalRoute(request: RouteRequest): Observable<RouteResponse> {
    return this.http.post<RouteResponse>(
      `${this.baseUrl}/optimization/calculate-optimal-route`,
      request,
    );
  }

  fetchPrices(): Observable<PriceResponse> {
    return this.http.get<PriceResponse>(`${this.baseUrl}/providers/austria-prices`);
  }
}
