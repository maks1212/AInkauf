export interface PriceRecord {
  store_id: string;
  product_key: string;
  price_eur: number;
  date: string;
  source: string;
}

export interface PriceResponse {
  count: number;
  items: PriceRecord[];
}
