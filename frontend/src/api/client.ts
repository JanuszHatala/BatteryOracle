import {
  ReportSummary,
  ReportDetail,
  TelemetryResponse,
  DiagnosisResponse,
  ComparativeResponse,
  Thread,
  Message,
  Settings,
  ModelsResponse,
  FetchLiveModelsResponse,
  PromptsResponse,
  PromptsMap,
  WifiRouter,
  DeviceProfile,
  DeviceProfileDetail,
  ProfileComparisonResponse,
  MasterSynthesisResponse,
  AccountingDashboardResponse,
  AiErrorDetail
} from '../types/api';

const BASE_URL = '/api/v1';

export class ApiClientError extends Error {
  status: number;
  aiError?: AiErrorDetail;

  constructor(message: string, status: number, aiError?: AiErrorDetail) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.aiError = aiError;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (!(options?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers
    }
  });

  if (!res.ok) {
    let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
    let aiError: AiErrorDetail | undefined;
    try {
      const errData = await res.json();
      if (errData.detail) {
        if (typeof errData.detail === 'object' && errData.detail.title) {
          aiError = errData.detail as AiErrorDetail;
          errorMsg = `${aiError.title}: ${aiError.raw_error || ''}`;
        } else if (typeof errData.detail === 'string') {
          errorMsg = errData.detail;
        } else {
          errorMsg = JSON.stringify(errData.detail);
        }
      }
    } catch {
      // ignore json parse failure
    }
    throw new ApiClientError(errorMsg, res.status, aiError);
  }

  return res.json();
}

export const api = {
  // Reports
  getReports: () => request<ReportSummary[]>('/reports'),

  getReport: (id: number) => request<ReportDetail>(`/reports/${id}`),

  uploadReport: (file: File, autoDiagnose = false, timezone?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_diagnose', String(autoDiagnose));
    if (timezone) {
      formData.append('timezone', timezone);
    }
    return request<ReportDetail>('/reports/upload', {
      method: 'POST',
      body: formData
    });
  },

  updateReport: (id: number, data: { custom_name?: string; description?: string; custom_night_start?: string | null; custom_night_end?: string | null; reset_night_window?: boolean }) =>
    request<ReportDetail>(`/reports/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),

  deleteReport: (id: number) =>
    request<{ deleted: boolean; id: number }>(`/reports/${id}`, {
      method: 'DELETE'
    }),

  getExportReportUrl: (id: number, scope = 'night') => `${BASE_URL}/reports/${id}/export-md?scope=${scope}`,

  // Telemetry
  getTelemetry: (id: number, scope = 'night', start?: string, end?: string) => {
    const params = new URLSearchParams({ scope });
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    return request<TelemetryResponse>(`/reports/${id}/telemetry?${params.toString()}`);
  },

  diagnoseReport: (id: number, scope = 'night', custom_start?: string, custom_end?: string) =>
    request<DiagnosisResponse>(`/reports/${id}/diagnose`, {
      method: 'POST',
      body: JSON.stringify({ scope, custom_start, custom_end })
    }),

  // Comparative
  analyzeComparative: (report_ids: number[], scope = 'night') =>
    request<ComparativeResponse>('/comparative/analyze', {
      method: 'POST',
      body: JSON.stringify({ report_ids, scope })
    }),

  getExportComparativeUrl: (reportIds: number[], scope = 'night') =>
    `${BASE_URL}/comparative/export-md?report_ids=${reportIds.join(',')}&scope=${scope}`,

  // Chat Threads
  getThreads: (reportId: number) => request<Thread[]>(`/reports/${reportId}/threads`),

  createThread: (reportId: number, title = 'New Investigation') =>
    request<Thread>(`/reports/${reportId}/threads`, {
      method: 'POST',
      body: JSON.stringify({ title })
    }),

  renameThread: (threadId: number, title: string) =>
    request<Thread>(`/threads/${threadId}`, {
      method: 'PUT',
      body: JSON.stringify({ title })
    }),

  deleteThread: (threadId: number) =>
    request<{ deleted: boolean; id: number }>(`/threads/${threadId}`, {
      method: 'DELETE'
    }),

  clearThread: (threadId: number) =>
    request<{ cleared: boolean; id: number }>(`/threads/${threadId}/clear`, {
      method: 'POST'
    }),

  getThreadMessages: (threadId: number) => request<Message[]>(`/threads/${threadId}/messages`),

  sendMessage: (threadId: number, content: string, filter_context = '') =>
    request<Message>(`/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, filter_context })
    }),

  toggleMessageCollapse: (messageId: number) =>
    request<Message>(`/messages/${messageId}/collapse`, {
      method: 'PUT'
    }),

  deleteMessage: (messageId: number) =>
    request<{ deleted: boolean; id: number }>(`/messages/${messageId}`, {
      method: 'DELETE'
    }),

  forkThread: (threadId: number, from_message_id: number, new_title = 'Forked Branch') =>
    request<Thread>(`/threads/${threadId}/fork`, {
      method: 'POST',
      body: JSON.stringify({ from_message_id, new_title })
    }),

  getExportThreadUrl: (threadId: number) => `${BASE_URL}/threads/${threadId}/export-md`,

  // Settings, Models & Prompts
  getSettings: () => request<Settings>('/settings'),

  updateSettings: (data: Partial<Settings> & { gemini_api_key?: string; openrouter_api_key?: string }) =>
    request<Settings>('/settings', {
      method: 'POST',
      body: JSON.stringify(data)
    }),

  getModels: (provider = 'Google Gemini') => request<ModelsResponse>(`/models?provider=${encodeURIComponent(provider)}`),

  fetchLiveModels: (provider: string, api_key?: string, api_base?: string) =>
    request<FetchLiveModelsResponse>('/models/fetch-live', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key, api_base })
    }),

  addCustomModel: (provider: string, model_name: string) =>
    request<ModelsResponse>('/models/custom', {
      method: 'POST',
      body: JSON.stringify({ provider, model_name })
    }),

  deleteCustomModel: (provider: string, model_name: string) =>
    request<ModelsResponse>(`/models/custom?provider=${encodeURIComponent(provider)}&model_name=${encodeURIComponent(model_name)}`, {
      method: 'DELETE'
    }),

  testConnection: (model: string, provider?: string, api_key?: string, api_base?: string) =>
    request<{ success: boolean; message: string }>('/settings/test-connection', {
      method: 'POST',
      body: JSON.stringify({ model, provider, api_key, api_base })
    }),

  getPrompts: () => request<PromptsResponse>('/prompts'),

  updatePrompts: (prompts: Partial<PromptsMap>) =>
    request<PromptsResponse>('/prompts', {
      method: 'PUT',
      body: JSON.stringify(prompts)
    }),

  resetPrompts: () =>
    request<PromptsResponse>('/prompts/reset', {
      method: 'POST'
    }),

  // Wi-Fi Routers
  getRouters: () => request<WifiRouter[]>('/wifi-routers'),

  discoverRouterSpecs: (brand: string, model: string) =>
    request<{ specs: Record<string, any>; error: string | null }>('/wifi-routers/discover', {
      method: 'POST',
      body: JSON.stringify({ brand, model })
    }),

  createRouter: (data: Omit<WifiRouter, 'id'>) =>
    request<WifiRouter>('/wifi-routers', {
      method: 'POST',
      body: JSON.stringify(data)
    }),

  updateRouter: (id: number, data: Partial<WifiRouter>) =>
    request<WifiRouter>(`/wifi-routers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),

  updateRouterStatus: (id: number, is_active: number) =>
    request<WifiRouter>(`/wifi-routers/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active })
    }),

  deleteRouter: (id: number) =>
    request<{ deleted: boolean; id: number }>(`/wifi-routers/${id}`, {
      method: 'DELETE'
    }),

  // Device Profiles
  getProfiles: () => request<DeviceProfile[]>('/device-profiles'),

  getProfile: (id: number) => request<DeviceProfileDetail>(`/device-profiles/${id}`),

  uploadProfile: (file: File, profileName?: string, profileId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (profileName) formData.append('profile_name', profileName);
    if (profileId) formData.append('profile_id', String(profileId));
    return request<DeviceProfileDetail>('/device-profiles/upload', {
      method: 'POST',
      body: formData
    });
  },

  renameProfile: (id: number, profile_name: string) =>
    request<DeviceProfileDetail>(`/device-profiles/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ profile_name })
    }),

  auditProfile: (id: number) =>
    request<DeviceProfileDetail>(`/device-profiles/${id}/audit`, {
      method: 'POST'
    }),

  compareProfiles: (profile_a: number, profile_b: number) =>
    request<ProfileComparisonResponse>(`/device-profiles/compare?profile_a=${profile_a}&profile_b=${profile_b}`),

  auditProfileComparison: (profile_a_id: number, profile_b_id: number) =>
    request<{ ai_analysis: string; updated_at: string; diff: Record<string, any> }>('/device-profiles/compare/audit', {
      method: 'POST',
      body: JSON.stringify({ profile_a_id, profile_b_id })
    }),

  deleteProfile: (id: number) =>
    request<{ deleted: boolean; id: number }>(`/device-profiles/${id}`, {
      method: 'DELETE'
    }),

  // Master Experiment Synthesis
  getMasterSynthesis: () => request<MasterSynthesisResponse>('/master-synthesis'),

  generateMasterSynthesis: () =>
    request<MasterSynthesisResponse>('/master-synthesis/generate', {
      method: 'POST'
    }),

  // Token & Cost Accounting
  getAccounting: () => request<AccountingDashboardResponse>('/accounting')
};
