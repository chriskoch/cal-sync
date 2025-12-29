import { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import { calendarsAPI, CalendarItem } from '../services/api';

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
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 3,
          bgcolor: '#f8f9fa',
          borderRadius: 2,
          border: '1px solid #dadce0',
        }}
      >
        <CircularProgress size={20} sx={{ mr: 2, color: '#1a73e8' }} />
        <Typography sx={{ fontSize: '14px', color: '#5f6368' }}>
          Loading calendars...
        </Typography>
      </Box>
    );
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
            borderColor: '#dadce0',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#1967d2',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#1a73e8',
          },
        }}
      >
        <MenuItem value="">
          <em>Select a calendar</em>
        </MenuItem>
        {calendars.map((calendar) => (
          <MenuItem key={calendar.id} value={calendar.id}>
            <Box>
              <Typography
                sx={{
                  fontSize: '14px',
                  color: '#202124',
                  fontWeight: calendar.is_primary ? 500 : 400,
                }}
              >
                {calendar.summary}
              </Typography>
              {calendar.is_primary && (
                <Typography
                  variant="caption"
                  sx={{
                    color: '#1967d2',
                    fontSize: '12px',
                  }}
                >
                  Primary calendar
                </Typography>
              )}
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
