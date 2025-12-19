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
} from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import CalendarSelector from './CalendarSelector';
import { syncAPI, SyncConfig } from '../services/api';

interface SyncConfigFormProps {
  onConfigCreated?: (config: SyncConfig) => void;
}

export default function SyncConfigForm({ onConfigCreated }: SyncConfigFormProps) {
  const [sourceCalendarId, setSourceCalendarId] = useState('');
  const [destCalendarId, setDestCalendarId] = useState('');
  const [syncLookaheadDays, setSyncLookaheadDays] = useState(90);
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
        syncLookaheadDays
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
              onChange={setSourceCalendarId}
              label="Source Calendar (sync FROM)"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <CalendarSelector
              accountType="destination"
              value={destCalendarId}
              onChange={setDestCalendarId}
              label="Destination Calendar (sync TO)"
            />
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
