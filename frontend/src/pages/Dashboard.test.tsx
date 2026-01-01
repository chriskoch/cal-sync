import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import Dashboard from './Dashboard'
import * as api from '../services/api'
import { mockUser } from '../test/mocks'

vi.mock('../services/api')
vi.mock('../context/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../context/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      logout: vi.fn(),
      loading: false,
      isAuthenticated: true,
    }),
  }
})

describe('Dashboard - Sync Deletion', () => {
  const mockOneWaySyncConfig = {
    id: 'sync-config-1',
    source_calendar_id: 'cal1@example.com',
    dest_calendar_id: 'cal2@example.com',
    is_active: true,
    sync_lookahead_days: 90,
    sync_direction: 'one_way',
    privacy_mode_enabled: false,
  }

  const mockBidirectionalForwardConfig = {
    id: 'forward-config-1',
    source_calendar_id: 'cal1@example.com',
    dest_calendar_id: 'cal2@example.com',
    is_active: true,
    sync_lookahead_days: 90,
    sync_direction: 'bidirectional_a_to_b',
    paired_config_id: 'forward-config-1', // Both configs use forward ID as pair ID
    privacy_mode_enabled: false,
  }

  const mockBidirectionalReverseConfig = {
    id: 'reverse-config-1',
    source_calendar_id: 'cal2@example.com',
    dest_calendar_id: 'cal1@example.com',
    is_active: true,
    sync_lookahead_days: 90,
    sync_direction: 'bidirectional_b_to_a',
    paired_config_id: 'forward-config-1', // Both configs use forward ID as pair ID
    privacy_mode_enabled: false,
  }

  const mockBidirectionalForwardConfigOrphan = {
    id: 'forward-orphan-1',
    source_calendar_id: 'cal3@example.com',
    dest_calendar_id: 'cal4@example.com',
    is_active: true,
    sync_lookahead_days: 90,
    sync_direction: 'bidirectional_a_to_b',
    paired_config_id: undefined,
    privacy_mode_enabled: false,
  }

  const mockOAuthStatus = {
    source_connected: true,
    source_email: 'source@example.com',
    destination_connected: true,
    destination_email: 'dest@example.com',
  }

  const mockCalendars = [
    { id: 'cal1@example.com', summary: 'Calendar 1' },
    { id: 'cal2@example.com', summary: 'Calendar 2' },
    { id: 'cal3@example.com', summary: 'Calendar 3' },
    { id: 'cal4@example.com', summary: 'Calendar 4' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock OAuth status
    vi.mocked(api.oauthAPI.getStatus).mockResolvedValue({
      data: mockOAuthStatus,
    } as any)

    // Mock calendars API
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValue({
      data: { calendars: mockCalendars },
    } as any)
  })

  describe('One-way sync deletion', () => {
    it('should remove config from UI immediately after deletion', async () => {
      // Setup: render with one-way sync config
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockOneWaySyncConfig],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockResolvedValue({
        data: {},
      } as any)

      render(<Dashboard />)

      // Wait for the sync config section to appear
      await waitFor(() => {
        expect(screen.getByText('Active syncs')).toBeInTheDocument()
        expect(screen.getByText('One-way sync')).toBeInTheDocument()
      })

      // Click the delete button in the one-way sync card
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1] // Last delete button is for the sync config
      await userEvent.click(configDeleteButton)

      // Confirm deletion in dialog
      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Verify API was called
      await waitFor(() => {
        expect(api.syncAPI.deleteConfig).toHaveBeenCalledWith('sync-config-1')
      })

      // Verify config section is removed from UI (optimistic update)
      await waitFor(() => {
        expect(screen.queryByText('One-way sync')).not.toBeInTheDocument()
      })

      // Verify success message
      expect(screen.getByText('Sync deleted successfully!')).toBeInTheDocument()
    })

    it('should show error message when deletion fails', async () => {
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockOneWaySyncConfig],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockRejectedValue({
        response: {
          data: {
            detail: 'Database error occurred',
          },
        },
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('One-way sync')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Verify error message is shown
      await waitFor(() => {
        expect(screen.getByText('Database error occurred')).toBeInTheDocument()
      })

      // Verify config is still in UI (deletion failed) - should find at least one
      expect(screen.queryAllByText('One-way sync').length).toBeGreaterThan(0)
    })
  })

  describe('Bi-directional sync deletion', () => {
    it('should delete both configs and remove from UI', async () => {
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockBidirectionalForwardConfig, mockBidirectionalReverseConfig],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockResolvedValue({
        data: {},
      } as any)

      render(<Dashboard />)

      // Wait for bi-directional sync to appear
      await waitFor(() => {
        expect(screen.getByText(/bi-directional sync/i)).toBeInTheDocument()
      })

      // Click the delete button for bi-directional sync
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      // Confirm deletion in dialog
      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Verify both configs are deleted via API (wait for both calls)
      await waitFor(() => {
        expect(api.syncAPI.deleteConfig).toHaveBeenCalledTimes(2)
      })

      expect(api.syncAPI.deleteConfig).toHaveBeenCalledWith('forward-config-1')
      expect(api.syncAPI.deleteConfig).toHaveBeenCalledWith('reverse-config-1')

      // Verify success message
      await waitFor(() => {
        expect(screen.getByText('Bi-directional sync deleted successfully!')).toBeInTheDocument()
      })

      // Verify the "Active syncs" section is gone (all configs deleted)
      expect(screen.queryByText('Active syncs')).not.toBeInTheDocument()
    })

    it('should handle missing reverse config without error', async () => {
      // This tests the fix for the 405 error bug
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockBidirectionalForwardConfigOrphan],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockResolvedValue({
        data: {},
      } as any)

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText(/bi-directional sync/i)).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Wait for deletion to complete
      await waitFor(() => {
        expect(api.syncAPI.deleteConfig).toHaveBeenCalled()
      })

      // CRITICAL: Verify deleteConfig was called exactly once with the forward ID
      expect(api.syncAPI.deleteConfig).toHaveBeenCalledTimes(1)
      expect(api.syncAPI.deleteConfig).toHaveBeenCalledWith('forward-orphan-1')

      // CRITICAL: Verify deleteConfig was NOT called with empty string (405 error fix)
      expect(api.syncAPI.deleteConfig).not.toHaveBeenCalledWith('')

      // Verify config is removed from UI - Active syncs section should be gone
      await waitFor(() => {
        expect(screen.queryByText('Active syncs')).not.toBeInTheDocument()
      })
    })

    it('should show error if bi-directional deletion fails', async () => {
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockBidirectionalForwardConfig, mockBidirectionalReverseConfig],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Failed to delete forward config',
          },
        },
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText(/bi-directional sync/i)).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Verify error message
      await waitFor(() => {
        expect(screen.getByText('Failed to delete forward config')).toBeInTheDocument()
      })

      // Verify configs are still in UI - should find at least one
      expect(screen.queryAllByText(/bi-directional sync/i).length).toBeGreaterThan(0)
    })
  })

  describe('Optimistic UI updates', () => {
    it('should remove config from UI immediately after confirmation', async () => {
      // Use a resolved promise so the delete completes normally
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockOneWaySyncConfig],
      } as any)

      vi.mocked(api.syncAPI.deleteConfig).mockResolvedValue({
        data: {},
      } as any)

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('One-way sync')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      const confirmButton = await screen.findByRole('button', { name: /^delete$/i })
      await userEvent.click(confirmButton)

      // Verify API was called
      await waitFor(() => {
        expect(api.syncAPI.deleteConfig).toHaveBeenCalledWith('sync-config-1')
      })

      // Config should be removed from UI (optimistic update + API completion)
      await waitFor(() => {
        expect(screen.queryByText('Active syncs')).not.toBeInTheDocument()
      })

      // Verify success message appears
      await waitFor(() => {
        expect(screen.getByText('Sync deleted successfully!')).toBeInTheDocument()
      })
    })
  })

  describe('Confirmation dialog', () => {
    it('should not delete config if user cancels confirmation', async () => {
      vi.mocked(api.syncAPI.listConfigs).mockResolvedValue({
        data: [mockOneWaySyncConfig],
      } as any)

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('One-way sync')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      const configDeleteButton = deleteButtons[deleteButtons.length - 1]
      await userEvent.click(configDeleteButton)

      // Wait for confirmation dialog
      await waitFor(() => {
        expect(screen.getByText(/delete sync configuration/i)).toBeInTheDocument()
      })

      // Click cancel button
      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await userEvent.click(cancelButton)

      // Verify API was NOT called
      expect(api.syncAPI.deleteConfig).not.toHaveBeenCalled()

      // Verify config is still in UI
      expect(screen.getByText('One-way sync')).toBeInTheDocument()
    })
  })
})
