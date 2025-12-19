import { vi } from 'vitest'

/**
 * Mock user data
 */
export const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

/**
 * Mock auth token
 */
export const mockToken = 'mock-jwt-token-12345'

/**
 * Mock OAuth status
 */
export const mockOAuthStatus = {
  source: {
    connected: true,
    email: 'source@example.com',
    expires_at: '2025-01-01T00:00:00Z',
  },
  destination: {
    connected: true,
    email: 'dest@example.com',
    expires_at: '2025-01-01T00:00:00Z',
  },
}

/**
 * Mock calendar list
 */
export const mockCalendars = [
  {
    id: 'calendar1@group.calendar.google.com',
    summary: 'Personal Calendar',
    description: 'My personal events',
    primary: true,
  },
  {
    id: 'calendar2@group.calendar.google.com',
    summary: 'Work Calendar',
    description: 'Work events',
    primary: false,
  },
]

/**
 * Mock sync configuration
 */
export const mockSyncConfig = {
  id: '456e7890-e89b-12d3-a456-426614174111',
  user_id: mockUser.id,
  source_calendar_id: mockCalendars[0].id,
  source_calendar_name: mockCalendars[0].summary,
  destination_calendar_id: mockCalendars[1].id,
  destination_calendar_name: mockCalendars[1].summary,
  sync_lookahead_days: 90,
  is_active: true,
  last_sync_at: '2024-01-15T10:30:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:30:00Z',
}

/**
 * Mock sync log
 */
export const mockSyncLog = {
  id: '789e0123-e89b-12d3-a456-426614174222',
  sync_config_id: mockSyncConfig.id,
  status: 'success',
  events_created: 5,
  events_updated: 3,
  events_deleted: 1,
  error_message: null,
  started_at: '2024-01-15T10:30:00Z',
  completed_at: '2024-01-15T10:30:30Z',
}

/**
 * Mock axios instance
 */
export const createMockAxios = () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  patch: vi.fn(),
  request: vi.fn(),
  interceptors: {
    request: { use: vi.fn(), eject: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn() },
  },
})

/**
 * Mock successful API responses
 */
export const mockApiResponses = {
  login: {
    access_token: mockToken,
    token_type: 'bearer',
  },
  register: mockUser,
  me: mockUser,
  oauthStatus: mockOAuthStatus,
  calendars: mockCalendars,
  syncConfigs: [mockSyncConfig],
  syncTrigger: {
    message: 'Sync completed successfully',
    log: mockSyncLog,
  },
  syncLogs: [mockSyncLog],
}
