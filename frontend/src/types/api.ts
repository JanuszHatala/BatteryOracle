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
    auto_start?: string | null;
    auto_end?: string | null;
    is_custom?: boolean;
  };
  session_bounds?: {
    min_time: string | null;
    max_time: string | null;
  };
}

export interface AiErrorDetail {
  category: 'rate_limit' | 'quota_exceeded' | 'auth' | 'connection' | 'model_not_found' | 'context_length' | 'unknown';
  title: string;
  icon: string;
  raw_error: string;
  suggestions: string[];
  retry_delay_sec: number | null;
  rate_limit_meta: {
    quota_metric?: string;
    quota_limit?: string;
    model?: string;
    is_free_tier?: boolean;
    is_daily_quota?: boolean;
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

export interface ProviderPresetInfo {
  name: string;
  default_model: string;
  default_base: string | null;
  requires_key: boolean;
}

export interface Settings {
  device_timezone: string;
  night_start_hour: number;
  night_end_hour: number;
  chat_enter_mode: 'newline' | 'send';
  active_llm_provider: string;
  active_llm_model: string;
  llm_api_key?: string;
  llm_api_base?: string;
  gemini_key_set: boolean;
  openrouter_key_set: boolean;
  providers?: ProviderPresetInfo[];
}

export interface ModelItemDetail {
  id: string;
  pricing: string;
  is_custom: boolean;
}

export interface ModelsResponse {
  provider: string;
  models: string[];
  model_details: ModelItemDetail[];
  custom_models: string[];
  default_model: string;
}

export interface FetchLiveModelsResponse {
  provider: string;
  models: string[];
  model_details: ModelItemDetail[];
  message: string;
}

export interface PromptsMap {
  single_diagnosis: string;
  comparison: string;
  chat_assistant: string;
  master_synthesis: string;
  profile_audit: string;
  profile_comparison: string;
  profile_chat: string;
}

export interface PromptsResponse {
  prompts: PromptsMap;
  defaults: PromptsMap;
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
  updated_at?: string;
}

export interface DeviceProfile {
  id: number;
  profile_name: string;
  device_model?: string;
  os_build?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DeviceProfileDetail {
  id: number;
  profile_name: string;
  device_model?: string;
  os_build?: string;
  raw_content: string;
  parsed_data: Record<string, any>;
  analysis_text: string;
  reasoning_trace: string;
  analysis_updated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ProfileComparisonResponse {
  profile_a: DeviceProfileDetail;
  profile_b: DeviceProfileDetail;
  diff: Record<string, any>;
  ai_analysis: string;
  updated_at: string;
}

export interface ScorecardItem {
  report_id: number;
  session_name: string;
  recorded_interval: string;
  full_drop_rate: string;
  night_standby_rate: string;
  total_loss: string;
  night_drop: string;
  notes: string;
}

export interface MasterSynthesisResponse {
  scorecard: ScorecardItem[];
  synthesis_text: string;
  reasoning_trace: string;
  updated_at: string | null;
  report_count: number;
  date_range: string;
}

export interface AccountingDashboardResponse {
  totals: {
    request_count: number;
    total_prompt: number;
    total_completion: number;
    total_cached: number;
    total_tokens: number;
    total_cost: number;
  };
  by_report: Array<{
    report_id: number | null;
    report_name: string;
    request_count: number;
    prompt_tokens: number;
    completion_tokens: number;
    cached_tokens: number;
    total_tokens: number;
    total_cost: number;
  }>;
  by_thread: Array<{
    thread_id: number | null;
    thread_title: string;
    report_name: string;
    request_count: number;
    total_tokens: number;
    total_cost: number;
  }>;
  over_time: Array<{
    date: string;
    model: string;
    request_count: number;
    prompt_tokens: number;
    completion_tokens: number;
    cached_tokens: number;
    total_tokens: number;
    total_cost: number;
  }>;
}
