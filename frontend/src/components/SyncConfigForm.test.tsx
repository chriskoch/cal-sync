import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import SyncConfigForm from './SyncConfigForm'
import * as api from '../services/api'
import { mockUser } from '../test/mocks'
import { CALENDAR_COLORS } from '../constants/colors'

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

describe('SyncConfigForm - Color Selection', () => {
  const mockCalendarsWithColors = [
    {
      id: 'cal1@example.com',
      summary: 'Business Calendar',
      color_id: '3', // Grape
    },
    {
      id: 'cal2@example.com',
      summary: 'Personal Calendar',
      color_id: '5', // Banana
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock calendars API with color information
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValue({
      data: { calendars: mockCalendarsWithColors },
    } as any)

    vi.mocked(api.syncAPI.createConfig).mockResolvedValue({
      data: {
        id: 'config-1',
        source_calendar_id: 'cal1@example.com',
        dest_calendar_id: 'cal2@example.com',
        is_active: true,
        sync_lookahead_days: 90,
        sync_direction: 'one_way',
        destination_color_id: '3',
        privacy_mode_enabled: false,
        privacy_placeholder_text: 'Personal appointment',
        paired_config_id: null,
        last_synced_at: null,
      },
    } as any)
  })

  it('should render color swatches grid', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Should have "Same as source" option + 11 color swatches = 12 total
    // Each color swatch is a clickable Box with title attribute
    const colorSwatches = screen.getAllByTitle(/Lavender|Sage|Grape|Flamingo|Banana|Tangerine|Peacock|Graphite|Blueberry|Basil|Tomato|Same as source/i)
    expect(colorSwatches.length).toBeGreaterThanOrEqual(11) // At least 11 colors
  })

  it('should pre-select source calendar color when calendar is selected', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Select source calendar (which has color_id: '3' = Grape)
    const sourceSelector = screen.getByLabelText(/calendar from account 1/i)
    await userEvent.click(sourceSelector)

    await waitFor(() => {
      const option = screen.getByRole('option', { name: /business calendar/i })
      expect(option).toBeInTheDocument()
    })

    const businessOption = screen.getByRole('option', { name: /business calendar/i })
    await userEvent.click(businessOption)

    // Wait for the color to be pre-selected
    await waitFor(() => {
      // The color name should be displayed
      const colorName = CALENDAR_COLORS.find(c => c.id === '3')?.name
      expect(screen.getByText(colorName!)).toBeInTheDocument()
    })
  })

  it('should show "Same as source calendar" when no color is selected', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Initially, should show "Same as source calendar"
    expect(screen.getByText(/same as source calendar/i)).toBeInTheDocument()
  })

  it('should display selected color name below picker', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Click on Lavender color
    const lavenderSwatch = screen.getByTitle(/Lavender/i)
    await userEvent.click(lavenderSwatch)

    // Should display "Lavender" below the picker
    await waitFor(() => {
      expect(screen.getByText('Lavender')).toBeInTheDocument()
    })
  })

  it('should show checkmark on selected color swatch', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Click on a color swatch
    const grapeSwatch = screen.getByTitle(/Grape/i)
    await userEvent.click(grapeSwatch)

    // Checkmark should appear (Check icon from MUI)
    await waitFor(() => {
      // The parent container of the swatch should contain the checkmark
      const swatchParent = grapeSwatch.parentElement
      const checkIcon = swatchParent?.querySelector('svg[data-testid="CheckIcon"]')
      expect(checkIcon).toBeInTheDocument()
    })
  })

  it('should show two color pickers for bi-directional sync', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Enable bidirectional sync
    const bidirectionalButton = screen.getByRole('button', { name: /bi-directional sync/i })
    await userEvent.click(bidirectionalButton)

    await waitFor(() => {
      // Should have two color picker sections
      const colorLabels = screen.getAllByText(/event color/i)
      expect(colorLabels.length).toBe(2)
    })
  })

  it('should allow independent color selection for each direction', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Enable bidirectional sync
    const bidirectionalButton = screen.getByRole('button', { name: /bi-directional sync/i })
    await userEvent.click(bidirectionalButton)

    await waitFor(() => {
      const colorLabels = screen.getAllByText(/event color/i)
      expect(colorLabels.length).toBe(2)
    })

    // Get all Lavender swatches (should be 2: one for each direction)
    const lavenderSwatches = screen.getAllByTitle(/Lavender/i)
    expect(lavenderSwatches.length).toBe(2)

    // Click first Lavender (forward direction)
    await userEvent.click(lavenderSwatches[0])

    // Get all Grape swatches
    const grapeSwatches = screen.getAllByTitle(/Grape/i)
    expect(grapeSwatches.length).toBe(2)

    // Click second Grape (reverse direction)
    await userEvent.click(grapeSwatches[1])

    await waitFor(() => {
      // Should show both color names (one for each direction)
      const lavenderTexts = screen.getAllByText('Lavender')
      const grapeTexts = screen.getAllByText('Grape')
      expect(lavenderTexts.length).toBeGreaterThanOrEqual(1)
      expect(grapeTexts.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('should select "Same as source" option when clicked', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // First select a color
    const lavenderSwatch = screen.getByTitle(/Lavender/i)
    await userEvent.click(lavenderSwatch)

    await waitFor(() => {
      expect(screen.getByText('Lavender')).toBeInTheDocument()
    })

    // Then click "Same as source"
    const sameAsSourceSwatch = screen.getByTitle(/Same as source/i)
    await userEvent.click(sameAsSourceSwatch)

    // Should show "Same as source calendar" again
    await waitFor(() => {
      expect(screen.getByText(/same as source calendar/i)).toBeInTheDocument()
    })
  })

  it('should create sync config with selected color', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Select calendars
    const sourceSelector = screen.getByLabelText(/calendar from account 1/i)
    await userEvent.click(sourceSelector)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /business calendar/i })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('option', { name: /business calendar/i }))

    const destSelector = screen.getByLabelText(/calendar from account 2/i)
    await userEvent.click(destSelector)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /personal calendar/i })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('option', { name: /personal calendar/i }))

    // Select a specific color (Flamingo = ID 4)
    const flamingoSwatch = screen.getByTitle(/Flamingo/i)
    await userEvent.click(flamingoSwatch)

    await waitFor(() => {
      expect(screen.getByText('Flamingo')).toBeInTheDocument()
    })

    // Submit form
    const submitButton = screen.getByRole('button', { name: /create sync/i })
    await userEvent.click(submitButton)

    // Verify API was called with correct color
    await waitFor(() => {
      expect(api.syncAPI.createConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          destination_color_id: '4', // Flamingo
        })
      )
    })
  })

  it('should create bi-directional sync with different colors per direction', async () => {
    render(<SyncConfigForm />)

    const createButton = screen.getByRole('button', { name: /create new sync/i })
    await userEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Enable bidirectional
    const bidirectionalButton = screen.getByRole('button', { name: /bi-directional sync/i })
    await userEvent.click(bidirectionalButton)

    await waitFor(() => {
      const colorLabels = screen.getAllByText(/event color/i)
      expect(colorLabels.length).toBe(2)
    })

    // Select calendars
    const sourceSelector = screen.getByLabelText(/calendar from account 1/i)
    await userEvent.click(sourceSelector)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /business calendar/i })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('option', { name: /business calendar/i }))

    const destSelector = screen.getByLabelText(/calendar from account 2/i)
    await userEvent.click(destSelector)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /personal calendar/i })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('option', { name: /personal calendar/i }))

    // Select different colors for each direction
    const lavenderSwatches = screen.getAllByTitle(/Lavender/i)
    await userEvent.click(lavenderSwatches[0]) // Forward direction

    const grapeSwatches = screen.getAllByTitle(/Grape/i)
    await userEvent.click(grapeSwatches[1]) // Reverse direction

    // Submit form
    const submitButton = screen.getByRole('button', { name: /create sync/i })
    await userEvent.click(submitButton)

    // Verify API was called with both colors
    await waitFor(() => {
      expect(api.syncAPI.createConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          destination_color_id: '1', // Lavender (forward)
          reverse_destination_color_id: '3', // Grape (reverse)
        })
      )
    })
  })
})
