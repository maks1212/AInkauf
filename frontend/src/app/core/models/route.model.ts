import { Location } from './location.model';
import { UserContext } from './user-context.model';

export interface ShoppingListItem {
  name: string;
  quantity: number;
  unit: string;
}

export interface StoreBasket {
  store_id: string;
  chain: string;
  location: Location;
  basket_total_eur: number;
  missing_items: number;
}

export interface RouteRequest {
  shopping_list: ShoppingListItem[];
  user: UserContext;
  energy_price_eur_per_unit?: number;
  stores: StoreBasket[];
}

export interface RouteStoreDecision {
  store_id: string;
  included: boolean;
  distance_km: number;
  basket_total_eur: number;
  mobility_cost_eur: number;
  fuel_cost_eur: number;
  net_savings_vs_baseline_eur: number;
  reason: string;
}

export interface RouteResponse {
  baseline_store_id: string;
  global_minimum_store_id: string;
  recommended_store_id: string;
  decisions: RouteStoreDecision[];
  estimated_total_eur: number;
  debug: Record<string, unknown>;
}
