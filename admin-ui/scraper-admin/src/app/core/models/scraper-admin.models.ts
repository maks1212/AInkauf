export interface ScraperConfig {
  enabled: boolean;
  interval_minutes: number;
  max_parallel_stores: number;
  retries: number;
  updated_at: string;
}

export interface ScheduleRecommendation {
  recommended_interval_minutes: number;
  min_interval_minutes: number;
  reasoning: string[];
  strategy: Record<string, number>;
}

export interface ScraperJob {
  id: string;
  status: string;
  source: string;
  stores: string[];
  store_count: number;
  record_count: number;
  inserted_count: number;
  matched_count: number;
  review_count: number;
  error_count: number;
  started_at: string;
  finished_at: string | null;
}

export interface CatalogItem {
  id: string;
  name: string;
  normalized_name: string;
  brand: string | null;
  serial_number: string | null;
  package_quantity: number | null;
  package_unit: string | null;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScrapedOffer {
  id: string;
  ingestion_run_id: string | null;
  source: string;
  source_store_id: string;
  source_product_key: string;
  source_serial_number: string | null;
  source_product_name: string;
  source_brand: string | null;
  source_category: string | null;
  source_package_quantity: number | null;
  source_package_unit: string | null;
  price_eur: number;
  currency: string;
  price_type: string;
  valid_from: string;
  valid_to: string | null;
  observed_at: string;
  canonical_product_id: string | null;
  mapping_confidence: number | null;
  needs_review: boolean;
  review_reason: string | null;
  promotion_type: string | null;
  promotion_label: string | null;
}

export interface ReviewItem {
  id: string;
  scraped_offer_id: string;
  status: string;
  review_reason: string | null;
  reviewer_note: string | null;
  resolved_canonical_product_id: string | null;
  created_at: string;
  resolved_at: string | null;
  updated_at: string;
}
