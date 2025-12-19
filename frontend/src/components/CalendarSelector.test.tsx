import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import CalendarSelector from './CalendarSelector'
import * as api from '../services/api'
import { mockCalendars } from '../test/mocks'

vi.mock('../services/api')

describe('CalendarSelector', () => {
  const mockOnChange = vi.fn()
  const defaultProps = {
    accountType: 'source' as const,
    value: '',
    onChange: mockOnChange,
    label: 'Source Calendar',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockImplementation(
      () => new Promise(() => {}) // Never resolves to keep loading state
    )

    render(<CalendarSelector {...defaultProps} />)

    expect(screen.getByText('Loading calendars...')).toBeInTheDocument()
  })

  it('displays error message when API call fails', async () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockRejectedValueOnce(
      new Error('API Error')
    )

    render(<CalendarSelector {...defaultProps} />)

    await waitFor(() => {
      expect(
        screen.getByText('Failed to fetch source calendars')
      ).toBeInTheDocument()
    })
  })

  it('displays calendars in dropdown after successful fetch', async () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValueOnce({
      data: { calendars: mockCalendars },
    } as any)

    render(<CalendarSelector {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByLabelText('Source Calendar')).toBeInTheDocument()
    })

    // Open the select dropdown
    const selectButton = screen.getByRole('combobox')
    await userEvent.click(selectButton)

    // Check that calendars are displayed
    expect(screen.getByText('Personal Calendar')).toBeInTheDocument()
    expect(screen.getByText('Work Calendar')).toBeInTheDocument()
    expect(screen.getByText('Primary Calendar')).toBeInTheDocument()
  })

  it('calls onChange when a calendar is selected', async () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValueOnce({
      data: { calendars: mockCalendars },
    } as any)

    render(<CalendarSelector {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByLabelText('Source Calendar')).toBeInTheDocument()
    })

    // Open the select dropdown
    const selectButton = screen.getByRole('combobox')
    await userEvent.click(selectButton)

    // Select a calendar
    const calendarOption = screen.getByText('Personal Calendar')
    await userEvent.click(calendarOption)

    // Verify onChange was called with correct calendar ID
    expect(mockOnChange).toHaveBeenCalledWith(mockCalendars[0].id)
  })

  it('fetches destination calendars when accountType is destination', async () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValueOnce({
      data: { calendars: mockCalendars },
    } as any)

    render(
      <CalendarSelector {...defaultProps} accountType="destination" />
    )

    await waitFor(() => {
      expect(api.calendarsAPI.listCalendars).toHaveBeenCalledWith('destination')
    })
  })

  it('displays selected value correctly', async () => {
    vi.mocked(api.calendarsAPI.listCalendars).mockResolvedValueOnce({
      data: { calendars: mockCalendars },
    } as any)

    render(
      <CalendarSelector {...defaultProps} value={mockCalendars[0].id} />
    )

    await waitFor(() => {
      const selectElement = screen.getByRole('combobox')
      expect(selectElement).toHaveTextContent('Personal Calendar')
    })
  })
})
