from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# --- Report Schemas ---

class ReportSummary(BaseModel):
    id: int
    filename: str
    custom_name: str
    description: Optional[str] = ""
    timestamp_str: Optional[str] = ""
    device_info: Optional[str] = ""
    rate_per_hr: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[str] = None


class ScopeAnalysisDetail(BaseModel):
    text: str = ""
    trace: Optional[str] = ""
    updated_at: Optional[str] = ""


class ReportDetail(BaseModel):
    id: int
    file_hash: str
    filename: str
    custom_name: str
    description: Optional[str] = ""
    timestamp_str: Optional[str] = ""
    device_info: Optional[str] = ""
    summary_text: str
    initial_analysis: str
    reasoning_trace: Optional[str] = ""
    custom_night_start: Optional[str] = None
    custom_night_end: Optional[str] = None
    analysis_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    analyses: Dict[str, ScopeAnalysisDetail] = Field(default_factory=dict)


class ReportUpdateRequest(BaseModel):
    custom_name: Optional[str] = None
    description: Optional[str] = None
    custom_night_start: Optional[str] = None
    custom_night_end: Optional[str] = None
    reset_night_window: Optional[bool] = False


# --- Telemetry & KPI Schemas ---

class TimelinePoint(BaseModel):
    timestamp: str
    battery_level: int
    screen_state: str


class PowerComponent(BaseModel):
    component: str
    mah: float
    percentage: Optional[float] = None


class KpiMetrics(BaseModel):
    start_time: str
    end_time: str
    start_level: int
    end_level: int
    drop_pct: int
    duration_hrs: float
    rate_per_hr: float
    status: str


class TelemetryResponse(BaseModel):
    scope: str
    kpis: KpiMetrics
    timeline: List[TimelinePoint]
    components: List[PowerComponent]
    night_bounds: Optional[Dict[str, Any]] = None
    session_bounds: Optional[Dict[str, Optional[str]]] = None


# --- Diagnosis & Comparative Schemas ---

class DiagnosisRequest(BaseModel):
    scope: str = "night"
    custom_start: Optional[str] = None
    custom_end: Optional[str] = None


class DiagnosisResponse(BaseModel):
    report_id: int
    scope: str
    diagnosis: str
    reasoning_trace: Optional[str] = ""
    updated_at: str
    analyses: Optional[Dict[str, ScopeAnalysisDetail]] = None


class ComparativeRequest(BaseModel):
    report_ids: List[int]
    scope: str = "night"


class ComparativeResponse(BaseModel):
    report_ids: List[int]
    scope: str
    analysis: str
    reasoning_trace: Optional[str] = ""
    cached: bool = False


# --- Chat & Thread Schemas ---

class ThreadCreateRequest(BaseModel):
    title: str = "New Investigation"


class ThreadRenameRequest(BaseModel):
    title: str


class ThreadResponse(BaseModel):
    id: int
    report_id: Optional[int] = None
    title: str
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageCreateRequest(BaseModel):
    content: str
    filter_context: Optional[str] = ""


class MessageResponse(BaseModel):
    id: int
    report_id: Optional[int] = None
    thread_id: Optional[int] = None
    role: str
    content: str
    filter_context: Optional[str] = ""
    is_collapsed: bool = False
    created_at: Optional[str] = None


class ThreadForkRequest(BaseModel):
    from_message_id: int
    new_title: Optional[str] = "Forked Investigation"


# --- Settings, Providers, Models & Prompts Schemas ---

class ProviderPresetInfo(BaseModel):
    name: str
    default_model: str
    default_base: Optional[str] = None
    requires_key: bool = True


class SettingsResponse(BaseModel):
    device_timezone: str = "Europe/Warsaw"
    night_start_hour: int = 23
    night_end_hour: int = 7
    chat_enter_mode: str = "newline"
    active_llm_provider: str = "Google Gemini"
    active_llm_model: str = "gemini/gemini-3.8-flash"
    llm_api_key: str = ""
    llm_api_base: str = ""
    gemini_key_set: bool = False
    openrouter_key_set: bool = False
    providers: List[ProviderPresetInfo] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    device_timezone: Optional[str] = None
    night_start_hour: Optional[int] = None
    night_end_hour: Optional[int] = None
    chat_enter_mode: Optional[str] = None
    active_llm_provider: Optional[str] = None
    active_llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


class ModelItemDetail(BaseModel):
    id: str
    pricing: str
    is_custom: bool = False


class ModelsResponse(BaseModel):
    provider: str
    models: List[str]
    model_details: List[ModelItemDetail] = Field(default_factory=list)
    custom_models: List[str] = Field(default_factory=list)
    default_model: str


class CustomModelRequest(BaseModel):
    provider: str
    model_name: str


class FetchLiveModelsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None


class FetchLiveModelsResponse(BaseModel):
    provider: str
    models: List[str]
    model_details: List[ModelItemDetail]
    message: str


class ConnectionTestRequest(BaseModel):
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    provider: Optional[str] = None


class PromptsUpdateRequest(BaseModel):
    single_diagnosis: Optional[str] = None
    comparison: Optional[str] = None
    chat_assistant: Optional[str] = None
    master_synthesis: Optional[str] = None
    profile_audit: Optional[str] = None
    profile_comparison: Optional[str] = None
    profile_chat: Optional[str] = None


# --- Device Profile & Wi-Fi Router Schemas ---

class DeviceProfileSummary(BaseModel):
    id: int
    profile_name: str
    device_model: Optional[str] = "Unknown Device"
    os_build: Optional[str] = "Unknown OS"
    is_active_context: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DeviceProfileDetail(BaseModel):
    id: int
    profile_name: str
    device_model: Optional[str] = "Unknown Device"
    os_build: Optional[str] = "Unknown OS"
    is_active_context: bool = False
    raw_content: str
    parsed_data: Dict[str, Any]
    analysis_text: Optional[str] = ""
    reasoning_trace: Optional[str] = ""
    analysis_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DeviceProfileUpdate(BaseModel):
    profile_name: str


class ProfileCompareRequest(BaseModel):
    profile_a_id: int
    profile_b_id: int


class WifiRouterCreate(BaseModel):
    router_name: str
    brand: str
    model: str
    specs_json: Dict[str, Any] = Field(default_factory=dict)
    location_tag: str = "Home"
    is_active: int = 1
    notes: Optional[str] = ""


class WifiRouterUpdate(BaseModel):
    is_active: Optional[int] = None
    router_name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    location_tag: Optional[str] = None
    notes: Optional[str] = None
    specs_json: Optional[Dict[str, Any]] = None


class RouterDiscoverRequest(BaseModel):
    brand: str
    model: str


class WifiRouterResponse(BaseModel):
    id: int
    router_name: str
    brand: str
    model: str
    specs_json: Dict[str, Any]
    location_tag: str
    is_active: int
    notes: Optional[str] = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# --- Master Experiment Synthesis & Accounting Schemas ---

class ScorecardItem(BaseModel):
    report_id: int
    session_name: str
    recorded_interval: str
    full_drop_rate: str
    night_standby_rate: str
    total_loss: str
    night_drop: str
    notes: str


class MasterSynthesisResponse(BaseModel):
    scorecard: List[ScorecardItem]
    synthesis_text: str = ""
    reasoning_trace: str = ""
    updated_at: Optional[str] = None
    report_count: int = 0
    date_range: str = ""


class AccountingDashboardResponse(BaseModel):
    totals: Dict[str, Any]
    by_report: List[Dict[str, Any]]
    by_thread: List[Dict[str, Any]]
    over_time: List[Dict[str, Any]]
