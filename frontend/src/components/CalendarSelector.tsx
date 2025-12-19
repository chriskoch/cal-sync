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
  onChange: (calendarId: string) => void;
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
      } catch (err: any) {
        setError(`Failed to fetch ${accountType} calendars`);
      } finally {
        setLoading(false);
      }
    };

    fetchCalendars();
  }, [accountType]);

  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', p: 2 }}>
        <CircularProgress size={20} sx={{ mr: 2 }} />
        <Typography>Loading calendars...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
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
      >
        <MenuItem value="">
          <em>Select a calendar</em>
        </MenuItem>
        {calendars.map((calendar) => (
          <MenuItem key={calendar.id} value={calendar.id}>
            <Box>
              <Typography variant="body1">{calendar.summary}</Typography>
              {calendar.is_primary && (
                <Typography variant="caption" color="primary">
                  Primary Calendar
                </Typography>
              )}
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
