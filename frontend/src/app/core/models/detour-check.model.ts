import { UserContext } from './user-context.model';

export interface DetourCheckRequest {
  base_store_total_eur: number;
  candidate_store_total_eur: number;
  detour_distance_km: number;
  user: UserContext;
  energy_price_eur_per_unit?: number;
}

export interface DetourCheckResponse {
  is_worth_it: boolean;
  gross_savings_eur: number;
  mobility_cost_eur: number;
  fuel_cost_eur: number;
  net_savings_eur: number;
  explanation: string;
}
