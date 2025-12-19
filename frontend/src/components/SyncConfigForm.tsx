import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Alert,
  Grid,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { PlayArrow, Circle } from '@mui/icons-material';
import CalendarSelector from './CalendarSelector';
import { syncAPI, SyncConfig } from '../services/api';

interface SyncConfigFormProps {
  onConfigCreated?: (config: SyncConfig) => void;
}

// Google Calendar color IDs and their corresponding colors
const CALENDAR_COLORS = [
  { id: '1', name: 'Lavender', color: '#7986cb' },
  { id: '2', name: 'Sage', color: '#33b679' },
  { id: '3', name: 'Grape', color: '#8e24aa' },
  { id: '4', name: 'Flamingo', color: '#e67c73' },
  { id: '5', name: 'Banana', color: '#f6c026' },
  { id: '6', name: 'Tangerine', color: '#f5511d' },
  { id: '7', name: 'Peacock', color: '#039be5' },
  { id: '8', name: 'Graphite', color: '#616161' },
  { id: '9', name: 'Blueberry', color: '#3f51b5' },
  { id: '10', name: 'Basil', color: '#0b8043' },
  { id: '11', name: 'Tomato', color: '#d60000' },
];

export default function SyncConfigForm({ onConfigCreated }: SyncConfigFormProps) {
  const [sourceCalendarId, setSourceCalendarId] = useState('');
  const [destCalendarId, setDestCalendarId] = useState('');
  const [syncLookaheadDays, setSyncLookaheadDays] = useState(90);
  const [destinationColorId, setDestinationColorId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!sourceCalendarId || !destCalendarId) {
      setError('Please select both source and destination calendars');
      return;
    }

    if (sourceCalendarId === destCalendarId) {
      setError('Source and destination calendars must be different');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const response = await syncAPI.createConfig(
        sourceCalendarId,
        destCalendarId,
        syncLookaheadDays,
        destinationColorId || undefined
      );

      setSuccess('Sync configuration created successfully!');
      if (onConfigCreated) {
        onConfigCreated(response.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create sync configuration');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Configure Calendar Sync
      </Typography>
      <Typography color="text.secondary" paragraph>
        Select which calendars you want to sync. Events from the source calendar will be
        copied to the destination calendar.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <CalendarSelector
              accountType="source"
              value={sourceCalendarId}
              onChange={(id, calendar) => {
                setSourceCalendarId(id);

                // Auto-select source calendar's color for destination
                if (calendar?.color_id && calendar.color_id.trim() !== '') {
                  // Check if the color_id is in our supported range (1-11)
                  // Event colors in Google Calendar only support IDs 1-11
                  const isValidColorId = CALENDAR_COLORS.some(c => c.id === calendar.color_id);
                  if (isValidColorId) {
                    setDestinationColorId(calendar.color_id);
                  } else {
                    // Color ID out of range for events, default to Lavender (1)
                    setDestinationColorId(CALENDAR_COLORS[0].id);
                  }
                } else if (calendar?.background_color) {
                  // Try to map background_color to a color ID
                  const matchedColor = CALENDAR_COLORS.find(
                    c => c.color.toLowerCase() === calendar.background_color?.toLowerCase()
                  );
                  if (matchedColor) {
                    setDestinationColorId(matchedColor.id);
                  } else {
                    // Default to first color if no match
                    setDestinationColorId(CALENDAR_COLORS[0].id);
                  }
                } else {
                  // No color information, use "Same as source"
                  setDestinationColorId('');
                }
              }}
              label="Source Calendar (sync FROM)"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <CalendarSelector
              accountType="destination"
              value={destCalendarId}
              onChange={(id) => setDestCalendarId(id)}
              label="Destination Calendar (sync TO)"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Destination Event Color</InputLabel>
              <Select
                value={destinationColorId}
                onChange={(e) => setDestinationColorId(e.target.value)}
                label="Destination Event Color"
              >
                <MenuItem value="">
                  <em>Same as source</em>
                </MenuItem>
                {CALENDAR_COLORS.map((colorOption) => (
                  <MenuItem key={colorOption.id} value={colorOption.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Circle sx={{ color: colorOption.color, fontSize: 16 }} />
                      {colorOption.name}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Sync Lookahead Days"
              value={syncLookaheadDays}
              onChange={(e) => setSyncLookaheadDays(Number(e.target.value))}
              helperText="How many days in the future to sync (default: 90)"
              inputProps={{ min: 1, max: 365 }}
            />
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={<PlayArrow />}
                disabled={loading || !sourceCalendarId || !destCalendarId}
              >
                {loading ? 'Creating...' : 'Create Sync Configuration'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
}
