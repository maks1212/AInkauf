import { Location } from './location.model';

export type TransportMode = 'car' | 'foot' | 'bike' | 'transit';
export type FuelType = 'diesel' | 'benzin' | 'autogas' | 'strom';

export interface UserContext {
  location: Location;
  transport_mode: TransportMode;
  vehicle_consumption_per_100km?: number;
  fuel_type?: FuelType;
  transit_cost_per_km_eur?: number;
}
