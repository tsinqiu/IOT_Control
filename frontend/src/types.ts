export type Grade = "green" | "yellow" | "orange" | "red" | "no_data" | string;

export interface SystemSummary {
  latest_timestamp: string;
  red_energy_count: number;
  orange_energy_count: number;
  low_health_pump_count: number;
  red_overflow_node_count: number;
  top_energy_pump: string;
  lowest_health_pump: string;
  highest_risk_node: string;
  system_energy_grade: Grade;
  system_safety_grade: Grade;
  system_overflow_grade: Grade;
}

export interface EnergyAssessment {
  timestamp: string;
  pump_id: string;
  pump_station_id: string;
  flow_cms_avg: number | null;
  energy_kwh_interval: number | null;
  interval_volume_m3: number | null;
  interval_unit_energy_kwh_per_kt: number | null;
  baseline_unit_energy_kwh_per_kt: number | null;
  energy_redundancy_ratio: number | null;
  self_redundancy_grade: Grade;
  unit_energy_rank_in_window: number | null;
  unit_energy_rank_count: number | null;
  unit_energy_percentile_in_window: number | null;
  cross_unit_energy_grade: Grade;
  energy_grade: Grade;
}

export interface PumpHealthAssessment {
  timestamp: string;
  pump_id: string;
  pump_station_id: string;
  startup_count_24h: number;
  runtime_min_24h: number;
  repeated_start_count_30min: number;
  continuous_runtime_min: number;
  max_forebay_percent_full: number | null;
  max_abs_level_change_rate_m_per_min: number | null;
  health_score: number;
  fatigue_index: number;
  safety_grade: Grade;
  deduction_detail: string;
}

export interface OverflowRiskAssessment {
  timestamp: string;
  node_id: string;
  x_coord: number | null;
  y_coord: number | null;
  level_ratio: number;
  level_score: number;
  rainfall_next_1h_mm: number;
  rainfall_next_2h_mm: number;
  rainfall_source_1h: string;
  rainfall_source_2h: string;
  rain_1h_score: number;
  rain_2h_score: number;
  flooding_history_score: number;
  overflow_risk_score: number;
  risk_grade: Grade;
}
