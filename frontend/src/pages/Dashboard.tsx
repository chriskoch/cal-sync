import { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  Alert,
  AppBar,
  Toolbar,
  Chip,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { CheckCircle, Cancel, ExitToApp, PlayArrow, Refresh, Delete, History, Circle, AccountCircle, Lock, SwapHoriz } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI, OAuthStatus, SyncConfig, syncAPI, calendarsAPI, CalendarItem } from '../services/api';
import SyncConfigForm from '../components/SyncConfigForm';
import SyncHistoryDialog from '../components/SyncHistoryDialog';

// Google Calendar color IDs and their corresponding colors
const CALENDAR_COLORS: { [key: string]: { name: string; color: string } } = {
  '1': { name: 'Lavender', color: '#7986cb' },
  '2': { name: 'Sage', color: '#33b679' },
  '3': { name: 'Grape', color: '#8e24aa' },
  '4': { name: 'Flamingo', color: '#e67c73' },
  '5': { name: 'Banana', color: '#f6c026' },
  '6': { name: 'Tangerine', color: '#f5511d' },
  '7': { name: 'Peacock', color: '#039be5' },
  '8': { name: 'Graphite', color: '#616161' },
  '9': { name: 'Blueberry', color: '#3f51b5' },
  '10': { name: 'Basil', color: '#0b8043' },
  '11': { name: 'Tomato', color: '#d60000' },
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
  const [syncConfigs, setSyncConfigs] = useState<SyncConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [syncingConfigId, setSyncingConfigId] = useState<string | null>(null);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [calendarNames, setCalendarNames] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    fetchOAuthStatus();
    fetchSyncConfigs();
    fetchCalendarNames();
  }, []);

  const fetchOAuthStatus = async () => {
    try {
      const response = await oauthAPI.getStatus();
      setOauthStatus(response.data);
    } catch (err: unknown) {
      console.error('Failed to fetch OAuth status:', err);
      setError('Failed to fetch OAuth status');
    } finally {
      setLoading(false);
    }
  };

  const fetchSyncConfigs = async () => {
    try {
      const response = await syncAPI.listConfigs();
      setSyncConfigs(response.data);
    } catch (err: unknown) {
      console.error('Failed to fetch sync configs:', err);
    }
  };

  const fetchCalendarNames = async () => {
    try {
      const nameMap: { [key: string]: string } = {};

      // Fetch source calendars
      try {
        const sourceResponse = await calendarsAPI.listCalendars('source');
        sourceResponse.data.calendars.forEach((cal: CalendarItem) => {
          nameMap[cal.id] = cal.summary;
        });
      } catch (err) {
        console.error('Failed to fetch source calendars:', err);
      }

      // Fetch destination calendars
      try {
        const destResponse = await calendarsAPI.listCalendars('destination');
        destResponse.data.calendars.forEach((cal: CalendarItem) => {
          nameMap[cal.id] = cal.summary;
        });
      } catch (err) {
        console.error('Failed to fetch destination calendars:', err);
      }

      setCalendarNames(nameMap);
    } catch (err: unknown) {
      console.error('Failed to fetch calendar names:', err);
    }
  };

  const getCalendarDisplayName = (calendarId: string): string => {
    return calendarNames[calendarId] || calendarId;
  };

  const handleTriggerSync = async (configId: string, triggerBothDirections = false) => {
    try {
      setSyncingConfigId(configId);
      setError('');
      setSuccess('');
      await syncAPI.triggerSync(configId, triggerBothDirections);

      // Wait a moment for the background task to complete
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Fetch the sync logs to get the results
      try {
        const logsResponse = await syncAPI.getSyncLogs(configId);
        if (logsResponse.data && logsResponse.data.length > 0) {
          const latestLog = logsResponse.data[0];
          setSuccess(
            `Sync completed! ${latestLog.events_created} events created, ` +
            `${latestLog.events_updated} updated, ${latestLog.events_deleted} deleted.`
          );
        } else {
          setSuccess('Sync completed successfully!');
        }
      } catch {
        setSuccess('Sync completed successfully!');
      }

      // Refresh the configs to get updated last_synced_at
      await fetchSyncConfigs();
      setSyncingConfigId(null);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to trigger sync');
      setSyncingConfigId(null);
    }
  };

  const handleDeleteConfig = async (configId: string) => {
    if (!window.confirm('Are you sure you want to delete this sync configuration? This action cannot be undone.')) {
      return;
    }

    try {
      setError('');
      setSuccess('');
      await syncAPI.deleteConfig(configId);
      setSuccess('Sync configuration deleted successfully!');
      // Refresh the configs list
      await fetchSyncConfigs();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to delete sync configuration');
    }
  };

  const handleViewHistory = (configId: string) => {
    setSelectedConfigId(configId);
    setHistoryDialogOpen(true);
  };

  const handleConnectAccount = async (accountType: 'source' | 'destination') => {
    try {
      const response = await oauthAPI.startOAuth(accountType);
      window.location.href = response.data.authorization_url;
    } catch (err: unknown) {
      console.error(`Failed to initiate OAuth for ${accountType} account:`, err);
      setError(`Failed to initiate OAuth for ${accountType} account`);
    }
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleLogoutClick = () => {
    handleUserMenuClose();
    logout();
  };

  const handleDeleteBidirectionalPair = async (forwardConfigId: string, reverseConfigId: string) => {
    if (!window.confirm('Are you sure you want to delete this bi-directional sync pair? This will delete both directions. This action cannot be undone.')) {
      return;
    }

    try {
      setError('');
      setSuccess('');
      // Delete both configs
      await syncAPI.deleteConfig(forwardConfigId);
      await syncAPI.deleteConfig(reverseConfigId);
      setSuccess('Bi-directional sync configuration deleted successfully!');
      // Refresh the configs list
      await fetchSyncConfigs();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to delete sync configuration');
    }
  };

  // Group configs into one-way and bidirectional
  const groupedConfigs = syncConfigs.reduce<{
    oneWay: SyncConfig[];
    bidirectional: { [key: string]: SyncConfig[] };
  }>(
    (acc, config) => {
      if (config.sync_direction.startsWith('bidirectional_')) {
        const pairId = config.paired_config_id || config.id;
        if (!acc.bidirectional[pairId]) {
          acc.bidirectional[pairId] = [];
        }
        acc.bidirectional[pairId].push(config);
      } else {
        acc.oneWay.push(config);
      }
      return acc;
    },
    { oneWay: [], bidirectional: {} }
  );

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Calendar Sync
          </Typography>
          <Typography variant="body1" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
          <IconButton
            color="inherit"
            onClick={handleUserMenuOpen}
            aria-label="user menu"
          >
            <AccountCircle />
          </IconButton>
          <Menu
            anchorEl={userMenuAnchor}
            open={Boolean(userMenuAnchor)}
            onClose={handleUserMenuClose}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
          >
            <MenuItem onClick={handleLogoutClick}>
              <ListItemIcon>
                <ExitToApp fontSize="small" />
              </ListItemIcon>
              <ListItemText>Logout</ListItemText>
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
            {success}
          </Alert>
        )}

        {loading ? (
          <Typography>Loading...</Typography>
        ) : (
          <Grid container spacing={3}>
            {/* Business Calendar Card */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    Business Calendar
                  </Typography>
                  <Typography color="text.secondary" gutterBottom>
                    Your first calendar for syncing
                  </Typography>

                  <Box sx={{ mt: 2, display: 'flex', alignItems: 'center' }}>
                    {oauthStatus?.source_connected ? (
                      <>
                        <CheckCircle color="success" sx={{ mr: 1 }} />
                        <Box>
                          <Typography variant="body1" fontWeight="bold">
                            Connected
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {oauthStatus.source_email}
                          </Typography>
                        </Box>
                      </>
                    ) : (
                      <>
                        <Cancel color="error" sx={{ mr: 1 }} />
                        <Typography>Not connected</Typography>
                      </>
                    )}
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    variant={oauthStatus?.source_connected ? 'outlined' : 'contained'}
                    onClick={() => handleConnectAccount('source')}
                  >
                    {oauthStatus?.source_connected ? 'Reconnect' : 'Connect Source Account'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>

            {/* Private Calendar Card */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    Private Calendar
                  </Typography>
                  <Typography color="text.secondary" gutterBottom>
                    Your second calendar for syncing
                  </Typography>

                  <Box sx={{ mt: 2, display: 'flex', alignItems: 'center' }}>
                    {oauthStatus?.destination_connected ? (
                      <>
                        <CheckCircle color="success" sx={{ mr: 1 }} />
                        <Box>
                          <Typography variant="body1" fontWeight="bold">
                            Connected
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {oauthStatus.destination_email}
                          </Typography>
                        </Box>
                      </>
                    ) : (
                      <>
                        <Cancel color="error" sx={{ mr: 1 }} />
                        <Typography>Not connected</Typography>
                      </>
                    )}
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    variant={oauthStatus?.destination_connected ? 'outlined' : 'contained'}
                    onClick={() => handleConnectAccount('destination')}
                  >
                    {oauthStatus?.destination_connected ? 'Reconnect' : 'Connect Destination Account'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>

            {/* Existing Sync Configurations */}
            {syncConfigs.length > 0 && (
              <Grid item xs={12}>
                <Paper sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h5">
                      Active Sync Configurations
                    </Typography>
                    <Button
                      startIcon={<Refresh />}
                      onClick={fetchSyncConfigs}
                      size="small"
                    >
                      Refresh
                    </Button>
                  </Box>
                  <Divider sx={{ mb: 2 }} />
                  <Grid container spacing={2}>
                    {/* Bi-directional configs */}
                    {Object.entries(groupedConfigs.bidirectional).map(([pairId, configs]) => {
                      const forwardConfig = configs.find(c => c.sync_direction === 'bidirectional_a_to_b');
                      const reverseConfig = configs.find(c => c.sync_direction === 'bidirectional_b_to_a');

                      if (!forwardConfig) return null;

                      return (
                        <Grid item xs={12} key={pairId}>
                          <Card variant="outlined" sx={{ borderColor: 'primary.main', borderWidth: 2 }}>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                                <SwapHoriz color="primary" />
                                <Typography variant="h6">Bi-Directional Sync</Typography>
                                <Chip label="↔" color="primary" size="small" />
                              </Box>

                              {/* Forward direction */}
                              <Box sx={{ mb: 2, pl: 2, borderLeft: '3px solid', borderColor: 'primary.main' }}>
                                <Typography variant="subtitle2" color="primary" gutterBottom>
                                  Forward: {getCalendarDisplayName(forwardConfig.source_calendar_id)} → {getCalendarDisplayName(forwardConfig.dest_calendar_id)}
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                  {forwardConfig.destination_color_id && CALENDAR_COLORS[forwardConfig.destination_color_id] && (
                                    <Chip
                                      icon={<Circle sx={{ color: `${CALENDAR_COLORS[forwardConfig.destination_color_id].color} !important` }} />}
                                      label={CALENDAR_COLORS[forwardConfig.destination_color_id].name}
                                      size="small"
                                      variant="outlined"
                                    />
                                  )}
                                  {forwardConfig.privacy_mode_enabled && (
                                    <Chip
                                      label={`Privacy: "${forwardConfig.privacy_placeholder_text}"`}
                                      size="small"
                                      icon={<Lock />}
                                      color="secondary"
                                    />
                                  )}
                                </Box>
                              </Box>

                              {/* Reverse direction */}
                              {reverseConfig && (
                                <Box sx={{ pl: 2, borderLeft: '3px solid', borderColor: 'secondary.main' }}>
                                  <Typography variant="subtitle2" color="secondary" gutterBottom>
                                    Reverse: {getCalendarDisplayName(reverseConfig.source_calendar_id)} → {getCalendarDisplayName(reverseConfig.dest_calendar_id)}
                                  </Typography>
                                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                    {reverseConfig.destination_color_id && CALENDAR_COLORS[reverseConfig.destination_color_id] && (
                                      <Chip
                                        icon={<Circle sx={{ color: `${CALENDAR_COLORS[reverseConfig.destination_color_id].color} !important` }} />}
                                        label={CALENDAR_COLORS[reverseConfig.destination_color_id].name}
                                        size="small"
                                        variant="outlined"
                                      />
                                    )}
                                    {reverseConfig.privacy_mode_enabled && (
                                      <Chip
                                        label={`Privacy: "${reverseConfig.privacy_placeholder_text}"`}
                                        size="small"
                                        icon={<Lock />}
                                        color="secondary"
                                      />
                                    )}
                                  </Box>
                                </Box>
                              )}

                              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                                Sync Lookahead: <strong>{forwardConfig.sync_lookahead_days} days</strong>
                              </Typography>
                              {forwardConfig.last_synced_at && (
                                <Typography variant="body2" color="text.secondary">
                                  Last Synced: <strong>{new Date(forwardConfig.last_synced_at).toLocaleString()}</strong>
                                </Typography>
                              )}
                            </CardContent>
                            <CardActions sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                              <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button
                                  variant="contained"
                                  startIcon={<PlayArrow />}
                                  onClick={() => handleTriggerSync(forwardConfig.id, true)}
                                  disabled={syncingConfigId === forwardConfig.id}
                                >
                                  {syncingConfigId === forwardConfig.id ? 'Syncing...' : 'Sync Both Directions'}
                                </Button>
                                <Button
                                  variant="outlined"
                                  startIcon={<History />}
                                  onClick={() => handleViewHistory(forwardConfig.id)}
                                >
                                  View History
                                </Button>
                              </Box>
                              <Button
                                variant="outlined"
                                color="error"
                                startIcon={<Delete />}
                                onClick={() =>
                                  handleDeleteBidirectionalPair(forwardConfig.id, reverseConfig?.id || '')
                                }
                              >
                                Delete Pair
                              </Button>
                            </CardActions>
                          </Card>
                        </Grid>
                      );
                    })}

                    {/* One-way configs */}
                    {groupedConfigs.oneWay.map((config) => (
                      <Grid item xs={12} key={config.id}>
                        <Card variant="outlined">
                          <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                              <Box>
                                <Typography variant="h6" gutterBottom>
                                  Sync Configuration
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Business: <strong>{getCalendarDisplayName(config.source_calendar_id)}</strong>
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Private: <strong>{getCalendarDisplayName(config.dest_calendar_id)}</strong>
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                  Sync Lookahead: <strong>{config.sync_lookahead_days} days</strong>
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                  {config.destination_color_id && CALENDAR_COLORS[config.destination_color_id] && (
                                    <Chip
                                      icon={<Circle sx={{ color: `${CALENDAR_COLORS[config.destination_color_id].color} !important` }} />}
                                      label={CALENDAR_COLORS[config.destination_color_id].name}
                                      size="small"
                                      variant="outlined"
                                    />
                                  )}
                                  {config.privacy_mode_enabled && (
                                    <Chip
                                      label={`Privacy: "${config.privacy_placeholder_text}"`}
                                      size="small"
                                      icon={<Lock />}
                                      color="secondary"
                                    />
                                  )}
                                </Box>
                                {config.last_synced_at && (
                                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                    Last Synced: <strong>{new Date(config.last_synced_at).toLocaleString()}</strong>
                                  </Typography>
                                )}
                              </Box>
                              <Box>
                                <Chip
                                  label={config.is_active ? 'Active' : 'Inactive'}
                                  color={config.is_active ? 'success' : 'default'}
                                  size="small"
                                />
                              </Box>
                            </Box>
                          </CardContent>
                          <CardActions sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Button
                                variant="contained"
                                startIcon={<PlayArrow />}
                                onClick={() => handleTriggerSync(config.id)}
                                disabled={syncingConfigId === config.id}
                              >
                                {syncingConfigId === config.id ? 'Syncing...' : 'Trigger Sync Now'}
                              </Button>
                              <Button
                                variant="outlined"
                                startIcon={<History />}
                                onClick={() => handleViewHistory(config.id)}
                              >
                                View History
                              </Button>
                            </Box>
                            <Button
                              variant="outlined"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDeleteConfig(config.id)}
                            >
                              Delete
                            </Button>
                          </CardActions>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
              </Grid>
            )}

            {/* Calendar Selection and Sync Configuration */}
            {oauthStatus?.source_connected && oauthStatus?.destination_connected && (
              <Grid item xs={12}>
                <SyncConfigForm
                  onConfigCreated={() => {
                    fetchSyncConfigs();
                  }}
                />
              </Grid>
            )}
          </Grid>
        )}
      </Container>

      {/* Sync History Dialog */}
      {selectedConfigId && (
        <SyncHistoryDialog
          open={historyDialogOpen}
          onClose={() => setHistoryDialogOpen(false)}
          configId={selectedConfigId}
        />
      )}
    </>
  );
}
