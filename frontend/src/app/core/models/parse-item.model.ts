export interface ParseRequest {
  text: string;
}

export interface ParseResponse {
  quantity: number;
  unit: string;
  product_name: string;
}
