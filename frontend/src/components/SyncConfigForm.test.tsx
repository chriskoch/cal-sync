import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import SyncConfigForm from './SyncConfigForm'
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

describe('SyncConfigForm - Privacy Settings UI', () => {
  const mockCalendars = [
    { id: 'cal1@example.com', summary: 'Business Calendar' },
    { id: 'cal2@example.com', summary: 'Personal Calendar' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock calendars API
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValue({
      data: { calendars: mockCalendars },
    } as any)

    // Mock create config API
    vi.mocked(api.syncAPI.createConfig).mockResolvedValue({
      data: {
        id: 'config-1',
        source_calendar_id: 'cal1@example.com',
        dest_calendar_id: 'cal2@example.com',
        is_active: true,
        sync_lookahead_days: 90,
        sync_direction: 'one_way',
        privacy_mode_enabled: false,
        privacy_placeholder_text: 'Personal appointment',
        paired_config_id: null,
        last_synced_at: null,
      },
    } as any)
  })

  it('should render the create sync button', () => {
    render(<SyncConfigForm />)
    expect(screen.getByRole('button', { name: /create new sync/i })).toBeInTheDocument()
  })

  it('should open dialog when create button is clicked', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should show privacy mode toggle', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/hide event details/i)).toBeInTheDocument()
    })
  })

  it('should show bi-directional sync toggle', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/bi-directional sync/i)).toBeInTheDocument()
    })
  })

  it('should show two privacy controls when bidirectional is enabled', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/bi-directional sync/i)).toBeInTheDocument()
    })

    // Enable bidirectional
    const bidirectionalLabel = screen.getByText(/bi-directional sync/i).closest('label')
    const bidirectionalSwitch = bidirectionalLabel?.querySelector('input[type="checkbox"]')

    if (bidirectionalSwitch) {
      await userEvent.click(bidirectionalSwitch)

      // Should show two "Hide event details" toggles
      await waitFor(() => {
        const hideDetailsTexts = screen.getAllByText(/hide event details/i)
        expect(hideDetailsTexts.length).toBe(2)
      })
    }
  })

  it('should show placeholder input when privacy is enabled', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/hide event details/i)).toBeInTheDocument()
    })

    // Privacy input should not be visible initially
    expect(screen.queryByLabelText(/placeholder text/i)).not.toBeInTheDocument()

    // Enable privacy
    const hideDetailsLabels = screen.getAllByText(/hide event details/i)
    const privacyLabel = hideDetailsLabels[0].closest('label')
    const privacySwitch = privacyLabel?.querySelector('input[type="checkbox"]')

    if (privacySwitch) {
      await userEvent.click(privacySwitch)

      // Now placeholder input should appear
      await waitFor(() => {
        expect(screen.getByLabelText(/placeholder text/i)).toBeInTheDocument()
      })
    }
  })

  it('should have default placeholder value', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/hide event details/i)).toBeInTheDocument()
    })

    // Enable privacy
    const hideDetailsLabels = screen.getAllByText(/hide event details/i)
    const privacyLabel = hideDetailsLabels[0].closest('label')
    const privacySwitch = privacyLabel?.querySelector('input[type="checkbox"]')

    if (privacySwitch) {
      await userEvent.click(privacySwitch)

      await waitFor(() => {
        const input = screen.getByLabelText(/placeholder text/i) as HTMLInputElement
        expect(input.value).toBe('Personal appointment')
      })
    }
  })
})
