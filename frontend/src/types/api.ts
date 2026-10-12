export interface ReportSummary {
  id: number;
  filename: string;
  custom_name: string;
  description: string;
  timestamp_str: string;
  device_info: string;
  rate_per_hr: number | null;
  status: string | null;
  created_at?: string;
}

export interface ReportDetail {
  id: number;
  file_hash: string;
  filename: string;
  custom_name: string;
  description: string;
  timestamp_str: string;
  device_info: string;
  summary_text: string;
  initial_analysis: string;
  reasoning_trace: string;
  custom_night_start: string | null;
  custom_night_end: string | null;
  analysis_updated_at: string | null;
  created_at: string | null;
}

export interface TimelinePoint {
  timestamp: string;
  battery_level: number;
  screen_state: string;
}

export interface PowerComponent {
  component: string;
  mah: number;
  percentage?: number;
}

export interface KpiMetrics {
  start_time: string;
  end_time: string;
  start_level: number;
  end_level: number;
  drop_pct: number;
  duration_hrs: number;
  rate_per_hr: number;
  status: string;
}

export interface TelemetryResponse {
  scope: string;
  kpis: KpiMetrics;
  timeline: TimelinePoint[];
  components: PowerComponent[];
  night_bounds?: {
    start: string | null;
    end: string | null;
  };
}

export interface DiagnosisResponse {
  report_id: number;
  scope: string;
  diagnosis: string;
  reasoning_trace: string;
  updated_at: string;
}

export interface ComparativeResponse {
  report_ids: number[];
  scope: string;
  analysis: string;
  reasoning_trace: string;
  cached: boolean;
}

export interface Thread {
  id: number;
  report_id: number | null;
  title: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface Message {
  id: number;
  report_id: number | null;
  thread_id: number;
  role: 'user' | 'assistant';
  content: string;
  filter_context: string;
  is_collapsed: boolean;
  created_at: string | null;
}

export interface Settings {
  device_timezone: string;
  night_start_hour: number;
  night_end_hour: number;
  chat_enter_mode: 'newline' | 'send';
  active_llm_provider: string;
  active_llm_model: string;
  gemini_key_set: boolean;
  openrouter_key_set: boolean;
}

export interface ModelsResponse {
  provider: string;
  models: string[];
  default_model: string;
}

export interface WifiRouter {
  id: number;
  router_name: string;
  brand: string;
  model: string;
  specs_json: Record<string, any>;
  location_tag: string;
  is_active: number;
  notes?: string;
  created_at?: string;
}

export interface DeviceProfile {
  id: number;
  profile_name: string;
  created_at?: string;
}
