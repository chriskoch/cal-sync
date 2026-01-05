import { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import { calendarsAPI, CalendarItem } from '../services/api';
import { LoadingBox, TypographyLabel } from './common';
import { APP_COLORS } from '../constants/colors';

interface CalendarSelectorProps {
  accountType: 'source' | 'destination';
  value: string;
  onChange: (calendarId: string, calendar?: CalendarItem) => void;
  label: string;
}

export default function CalendarSelector({
  accountType,
  value,
  onChange,
  label,
}: CalendarSelectorProps) {
  const [calendars, setCalendars] = useState<CalendarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        setLoading(true);
        const response = await calendarsAPI.listCalendars(accountType);
        setCalendars(response.data.calendars);
        setError('');
      } catch (err: unknown) {
        console.error(`Failed to fetch ${accountType} calendars:`, err);
        setError(`Failed to fetch ${accountType} calendars`);
      } finally {
        setLoading(false);
      }
    };

    fetchCalendars();
  }, [accountType]);

  const handleChange = (event: SelectChangeEvent) => {
    const selectedId = event.target.value;
    const selectedCalendar = calendars.find(cal => cal.id === selectedId);
    onChange(selectedId, selectedCalendar);
  };

  if (loading) {
    return <LoadingBox message="Loading calendars..." size={20} />;
  }

  if (error) {
    return (
      <Alert
        severity="error"
        sx={{
          borderRadius: 2,
          '& .MuiAlert-icon': {
            fontSize: 20,
          },
        }}
      >
        {error}
      </Alert>
    );
  }

  return (
    <FormControl fullWidth>
      <InputLabel id={`${accountType}-calendar-label`}>{label}</InputLabel>
      <Select
        labelId={`${accountType}-calendar-label`}
        id={`${accountType}-calendar-select`}
        value={value}
        label={label}
        onChange={handleChange}
        sx={{
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: APP_COLORS.surface.border,
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: APP_COLORS.brand.secondary,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: APP_COLORS.brand.primary,
          },
        }}
      >
        <MenuItem value="">
          <em>Select a calendar</em>
        </MenuItem>
        {calendars.map((calendar) => (
          <MenuItem key={calendar.id} value={calendar.id}>
            <Box>
              <TypographyLabel
                sx={{
                  fontWeight: calendar.is_primary ? 500 : 400,
                }}
              >
                {calendar.summary}
              </TypographyLabel>
              {calendar.is_primary && (
                <TypographyLabel
                  variant="caption"
                  sx={{
                    color: APP_COLORS.brand.secondary,
                  }}
                >
                  Primary calendar
                </TypographyLabel>
              )}
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
