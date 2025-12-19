import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (redirect to login)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Type definitions
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
}

export interface OAuthStatus {
  source_connected: boolean;
  source_email?: string;
  destination_connected: boolean;
  destination_email?: string;
}

export interface CalendarItem {
  id: string;
  summary: string;
  description?: string;
  time_zone?: string;
  access_role?: string;
  is_primary?: boolean;
  background_color?: string;
  color_id?: string;
}

export interface SyncConfig {
  id: string;
  source_calendar_id: string;
  dest_calendar_id: string;
  is_active: boolean;
  sync_lookahead_days: number;
  destination_color_id?: string;
  last_synced_at?: string;
}

export interface SyncLog {
  id: string;
  events_created: number;
  events_updated: number;
  events_deleted: number;
  status: string;
  error_message?: string;
  sync_window_start: string;
  sync_window_end: string;
  started_at: string;
  completed_at?: string;
}

// API methods
export const authAPI = {
  register: (email: string, password: string, full_name?: string) =>
    api.post<User>('/auth/register', { email, password, full_name }),

  login: (username: string, password: string) =>
    api.post<{ access_token: string; token_type: string }>('/auth/token',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),

  getCurrentUser: () => api.get<User>('/auth/me'),
};

export const oauthAPI = {
  startOAuth: (accountType: 'source' | 'destination') =>
    api.get<{ authorization_url: string }>(`/oauth/start/${accountType}`),

  getStatus: () => api.get<OAuthStatus>('/oauth/status'),
};

export const calendarsAPI = {
  listCalendars: (accountType: 'source' | 'destination') =>
    api.get<{ calendars: CalendarItem[] }>(`/calendars/${accountType}/list`),
};

export const syncAPI = {
  createConfig: (source_calendar_id: string, dest_calendar_id: string, sync_lookahead_days = 90, destination_color_id?: string) =>
    api.post<SyncConfig>('/sync/config', { source_calendar_id, dest_calendar_id, sync_lookahead_days, destination_color_id }),

  listConfigs: () => api.get<SyncConfig[]>('/sync/config'),

  deleteConfig: (configId: string) => api.delete(`/sync/config/${configId}`),

  triggerSync: (configId: string) =>
    api.post<{ message: string; sync_log_id: string }>(`/sync/trigger/${configId}`),

  getSyncLogs: (configId: string) => api.get<SyncLog[]>(`/sync/logs/${configId}`),
};
