export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
}

export interface CurrencyRates {
  usd_to_rub: number;
  eur_to_rub: number;
  gel_to_rub: number;
}

export interface CalculatorRequest {
  car_price_usd: number;
  engine_volume_cc: number;
  car_year: number;
  horse_power: number;
  source_make?: string | null;
  source_model?: string | null;
  source_model_id?: number | null;
  powertrain_kind?: "ICE" | "OTHER_HYBRID" | "EV" | "SERIES_HYBRID" | null;
  is_personal_use?: boolean;
  logistics_cost_rub: number;
  rf_analog_price_rub?: number | null;
  note?: string | null;
}

export interface CalculatorResult {
  car_price_rub: number;
  customs_fee_rub?: number | null;
  customs_duty_rub: number;
  recycling_fee_rub: number;
  logistics_cost_rub: number;
  total_cost_rub: number;
  savings_vs_rf_rub?: number | null;
  rates: CurrencyRates;
}

export interface CalculationOut extends CalculatorRequest {
  id: number;
  customs_duty_rub: number;
  recycling_fee_rub: number;
  total_cost_rub: number;
  usd_to_rub: number;
  eur_to_rub: number;
  gel_to_rub: number;
  created_at: string;
}

export interface CarListing {
  car_id: number;
  category_id?: number | null;
  make: string;
  model_id?: number | null;
  car_model?: string | null;
  model: string;
  year: number;
  price_usd: number;
  engine_volume_cc: number;
  horse_power?: number | null;
  horse_power_source?: string | null;
  fuel_type?: string | null;
  util_coefficient?: number | null;
  powertrain_kind?: "ICE" | "OTHER_HYBRID" | "EV" | "SERIES_HYBRID" | null;
  mileage_km?: number | null;
  image_url?: string | null;
  image_urls?: string[];
  url: string;
  estimated_total_rub?: number | null;
}

export interface CarMakeOption {
  man_id: number;
  title: string;
}

export interface CarModelOption {
  model_id: number;
  man_id: number;
  title: string;
  group_title?: string | null;
}
