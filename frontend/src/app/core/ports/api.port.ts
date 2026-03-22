import { Observable } from 'rxjs';
import { ParseRequest, ParseResponse } from '../models/parse-item.model';
import { DetourCheckRequest, DetourCheckResponse } from '../models/detour-check.model';
import { RouteRequest, RouteResponse } from '../models/route.model';
import { PriceResponse } from '../models/price.model';

export abstract class AInkaufApiPort {
  abstract healthCheck(): Observable<{ status: string }>;
  abstract parseItem(request: ParseRequest): Observable<ParseResponse>;
  abstract detourCheck(request: DetourCheckRequest): Observable<DetourCheckResponse>;
  abstract calculateOptimalRoute(request: RouteRequest): Observable<RouteResponse>;
  abstract fetchPrices(): Observable<PriceResponse>;
}
