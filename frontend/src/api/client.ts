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
  WifiRouter,
  DeviceProfile
} from '../types/api';

const BASE_URL = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = data.detail;
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // Reports
  getReports: () => request<ReportSummary[]>('/reports'),
  
  getReport: (id: number) => request<ReportDetail>(`/reports/${id}`),
  
  uploadReport: async (file: File, autoDiagnose = false, timezone = 'UTC') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_diagnose', String(autoDiagnose));
    formData.append('timezone', timezone);
    return request<ReportDetail>('/reports/upload', {
      method: 'POST',
      body: formData
    });
  },

  updateReport: (id: number, data: { custom_name?: string; description?: string; custom_night_start?: string; custom_night_end?: string }) =>
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

  // Settings
  getSettings: () => request<Settings>('/settings'),

  updateSettings: (data: Partial<Settings> & { gemini_api_key?: string; openrouter_api_key?: string }) =>
    request<Settings>('/settings', {
      method: 'POST',
      body: JSON.stringify(data)
    }),

  getModels: (provider = 'Google Gemini') => request<ModelsResponse>(`/models?provider=${encodeURIComponent(provider)}`),

  testConnection: (model: string, provider?: string, api_key?: string) =>
    request<{ success: boolean; message: string }>('/settings/test-connection', {
      method: 'POST',
      body: JSON.stringify({ model, provider, api_key })
    }),

  // Wi-Fi Routers
  getRouters: () => request<WifiRouter[]>('/wifi-routers'),

  createRouter: (data: Omit<WifiRouter, 'id'>) =>
    request<WifiRouter>('/wifi-routers', {
      method: 'POST',
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

  uploadProfile: (file: File, profileName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (profileName) formData.append('profile_name', profileName);
    return request<DeviceProfile>('/device-profiles/upload', {
      method: 'POST',
      body: formData
    });
  },

  deleteProfile: (id: number) =>
    request<{ deleted: boolean; id: number }>(`/device-profiles/${id}`, {
      method: 'DELETE'
    })
};
