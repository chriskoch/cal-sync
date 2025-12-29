import { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Alert,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  ExitToApp,
  PlayArrow,
  Refresh,
  Delete,
  History,
  Circle,
  AccountCircle,
  Lock,
  SwapHoriz,
  ArrowForward,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI, OAuthStatus, SyncConfig, syncAPI, calendarsAPI, CalendarItem } from '../services/api';
import SyncConfigForm from '../components/SyncConfigForm';
import SyncHistoryDialog from '../components/SyncHistoryDialog';
import ConfirmDialog from '../components/ConfirmDialog';

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

  // Confirmation dialog state
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmDialogConfig, setConfirmDialogConfig] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    title: '',
    message: '',
    onConfirm: () => {},
  });
  const [deletingConfig, setDeletingConfig] = useState(false);

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

  const handleDeleteConfig = (configId: string) => {
    setConfirmDialogConfig({
      title: 'Delete sync configuration?',
      message: 'This sync configuration will be permanently deleted. This action cannot be undone.',
      onConfirm: async () => {
        try {
          setDeletingConfig(true);
          setError('');
          setSuccess('');
          await syncAPI.deleteConfig(configId);
          setConfirmDialogOpen(false);
          setSuccess('Sync deleted successfully!');
          // Refresh the configs list
          await fetchSyncConfigs();
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } };
          setError(error.response?.data?.detail || 'Failed to delete sync configuration');
          setConfirmDialogOpen(false);
        } finally {
          setDeletingConfig(false);
        }
      },
    });
    setConfirmDialogOpen(true);
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

  const handleDeleteBidirectionalPair = (forwardConfigId: string, reverseConfigId: string) => {
    setConfirmDialogConfig({
      title: 'Delete bi-directional sync?',
      message: 'This will permanently delete both sync directions. This action cannot be undone.',
      onConfirm: async () => {
        try {
          setDeletingConfig(true);
          setError('');
          setSuccess('');
          // Delete both configs
          await syncAPI.deleteConfig(forwardConfigId);
          await syncAPI.deleteConfig(reverseConfigId);
          setConfirmDialogOpen(false);
          setSuccess('Bi-directional sync deleted successfully!');
          // Refresh the configs list
          await fetchSyncConfigs();
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } };
          setError(error.response?.data?.detail || 'Failed to delete sync configuration');
          setConfirmDialogOpen(false);
        } finally {
          setDeletingConfig(false);
        }
      },
    });
    setConfirmDialogOpen(true);
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
    <Box sx={{
      minHeight: '100vh',
      bgcolor: '#f8f9fa',
    }}>
      {/* Header */}
      <Box
        component="header"
        sx={{
          bgcolor: 'white',
          borderBottom: '1px solid',
          borderColor: 'divider',
          px: 3,
          py: 2,
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 400,
                fontSize: '22px',
                color: '#202124',
                letterSpacing: '-0.2px',
              }}
            >
              Calendar Sync
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  color: '#5f6368',
                  fontSize: '14px',
                }}
              >
                {user?.email}
              </Typography>
              <IconButton
                onClick={handleUserMenuOpen}
                size="small"
                sx={{
                  color: '#5f6368',
                  '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                }}
              >
                <AccountCircle />
              </IconButton>
              <Menu
                anchorEl={userMenuAnchor}
                open={Boolean(userMenuAnchor)}
                onClose={handleUserMenuClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                transformOrigin={{ vertical: 'top', horizontal: 'right' }}
                slotProps={{
                  paper: {
                    elevation: 0,
                    sx: {
                      mt: 1,
                      border: '1px solid',
                      borderColor: 'divider',
                      boxShadow: '0 1px 2px 0 rgba(60,64,67,.3), 0 2px 6px 2px rgba(60,64,67,.15)',
                    },
                  },
                }}
              >
                <MenuItem onClick={handleLogoutClick}>
                  <ListItemIcon>
                    <ExitToApp fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>Sign out</ListItemText>
                </MenuItem>
              </Menu>
            </Box>
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        {/* Alerts */}
        {error && (
          <Alert
            severity="error"
            sx={{ mb: 3, borderRadius: 2 }}
            onClose={() => setError('')}
          >
            {error}
          </Alert>
        )}

        {success && (
          <Alert
            severity="success"
            sx={{ mb: 3, borderRadius: 2 }}
            onClose={() => setSuccess('')}
          >
            {success}
          </Alert>
        )}

        {loading ? (
          <Typography sx={{ color: '#5f6368', py: 4, textAlign: 'center' }}>
            Loading...
          </Typography>
        ) : (
          <Stack spacing={3}>
            {/* Account Connection Status */}
            <Box>
              <Typography
                variant="h5"
                sx={{
                  fontSize: '24px',
                  fontWeight: 400,
                  color: '#202124',
                  mb: 2,
                  letterSpacing: '-0.3px',
                }}
              >
                Accounts
              </Typography>
              <Grid container spacing={2}>
                {/* Business Calendar */}
                <Grid item xs={12} md={6}>
                  <Card
                    elevation={0}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 3,
                      bgcolor: 'white',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        boxShadow: '0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15)',
                      },
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Typography
                        variant="subtitle1"
                        sx={{
                          fontSize: '16px',
                          fontWeight: 500,
                          color: '#202124',
                          mb: 0.5,
                        }}
                      >
                        Account 1
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '14px',
                          color: '#5f6368',
                          mb: 2.5,
                        }}
                      >
                        Events will be synced FROM calendars in this account
                      </Typography>

                      {oauthStatus?.source_connected ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <CheckCircle sx={{ fontSize: 20, color: '#1e8e3e' }} />
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: '#202124',
                                fontWeight: 500,
                              }}
                            >
                              Connected
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '13px',
                                color: '#5f6368',
                              }}
                            >
                              {oauthStatus.source_email}
                            </Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Cancel sx={{ fontSize: 20, color: '#d93025' }} />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: '#5f6368',
                            }}
                          >
                            Not connected
                          </Typography>
                        </Box>
                      )}
                    </CardContent>
                    <CardActions sx={{ px: 3, pb: 2.5, pt: 0 }}>
                      {oauthStatus?.source_connected ? (
                        <Tooltip title="Replace this account connection with a different Google account">
                          <Button
                            variant="outlined"
                            onClick={() => handleConnectAccount('source')}
                            sx={{
                              textTransform: 'none',
                              fontSize: '14px',
                              fontWeight: 500,
                              borderRadius: 2,
                              px: 3,
                              borderColor: '#dadce0',
                              color: '#1967d2',
                              '&:hover': {
                                borderColor: '#1967d2',
                                bgcolor: 'rgba(26, 115, 232, 0.04)',
                              },
                            }}
                          >
                            Reconnect
                          </Button>
                        </Tooltip>
                      ) : (
                        <Button
                          variant="contained"
                          onClick={() => handleConnectAccount('source')}
                          sx={{
                            textTransform: 'none',
                            fontSize: '14px',
                            fontWeight: 500,
                            borderRadius: 2,
                            px: 3,
                            bgcolor: '#1a73e8',
                            '&:hover': {
                              bgcolor: '#1765cc',
                            },
                          }}
                        >
                          Connect account
                        </Button>
                      )}
                    </CardActions>
                  </Card>
                </Grid>

                {/* Private Calendar */}
                <Grid item xs={12} md={6}>
                  <Card
                    elevation={0}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 3,
                      bgcolor: 'white',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        boxShadow: '0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15)',
                      },
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Typography
                        variant="subtitle1"
                        sx={{
                          fontSize: '16px',
                          fontWeight: 500,
                          color: '#202124',
                          mb: 0.5,
                        }}
                      >
                        Account 2
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '14px',
                          color: '#5f6368',
                          mb: 2.5,
                        }}
                      >
                        Events will be synced TO calendars in this account
                      </Typography>

                      {oauthStatus?.destination_connected ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <CheckCircle sx={{ fontSize: 20, color: '#1e8e3e' }} />
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: '#202124',
                                fontWeight: 500,
                              }}
                            >
                              Connected
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '13px',
                                color: '#5f6368',
                              }}
                            >
                              {oauthStatus.destination_email}
                            </Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Cancel sx={{ fontSize: 20, color: '#d93025' }} />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: '#5f6368',
                            }}
                          >
                            Not connected
                          </Typography>
                        </Box>
                      )}
                    </CardContent>
                    <CardActions sx={{ px: 3, pb: 2.5, pt: 0 }}>
                      {oauthStatus?.destination_connected ? (
                        <Tooltip title="Replace this account connection with a different Google account">
                          <Button
                            variant="outlined"
                            onClick={() => handleConnectAccount('destination')}
                            sx={{
                              textTransform: 'none',
                              fontSize: '14px',
                              fontWeight: 500,
                              borderRadius: 2,
                              px: 3,
                              borderColor: '#dadce0',
                              color: '#1967d2',
                              '&:hover': {
                                borderColor: '#1967d2',
                                bgcolor: 'rgba(26, 115, 232, 0.04)',
                              },
                            }}
                          >
                            Reconnect
                          </Button>
                        </Tooltip>
                      ) : (
                        <Button
                          variant="contained"
                          onClick={() => handleConnectAccount('destination')}
                          sx={{
                            textTransform: 'none',
                            fontSize: '14px',
                            fontWeight: 500,
                            borderRadius: 2,
                            px: 3,
                            bgcolor: '#1a73e8',
                            '&:hover': {
                              bgcolor: '#1765cc',
                            },
                          }}
                        >
                          Connect account
                        </Button>
                      )}
                    </CardActions>
                  </Card>
                </Grid>
              </Grid>
            </Box>

            {/* Active Sync Configurations */}
            {syncConfigs.length > 0 && (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography
                    variant="h5"
                    sx={{
                      fontSize: '24px',
                      fontWeight: 400,
                      color: '#202124',
                      letterSpacing: '-0.3px',
                    }}
                  >
                    Active syncs
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {oauthStatus?.source_connected && oauthStatus?.destination_connected && (
                      <SyncConfigForm
                        onConfigCreated={() => {
                          fetchSyncConfigs();
                        }}
                      />
                    )}
                    <IconButton
                      size="small"
                      onClick={fetchSyncConfigs}
                      sx={{
                        color: '#5f6368',
                        '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                      }}
                    >
                      <Refresh fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>

                <Stack spacing={2}>
                  {/* Bi-directional configs */}
                  {Object.entries(groupedConfigs.bidirectional).map(([pairId, configs]) => {
                    const forwardConfig = configs.find(c => c.sync_direction === 'bidirectional_a_to_b');
                    const reverseConfig = configs.find(c => c.sync_direction === 'bidirectional_b_to_a');

                    if (!forwardConfig) return null;

                    return (
                      <Card
                        key={pairId}
                        elevation={0}
                        sx={{
                          border: '1px solid',
                          borderColor: '#1a73e8',
                          borderRadius: 3,
                          bgcolor: 'white',
                          overflow: 'visible',
                        }}
                      >
                        <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
                            <SwapHoriz sx={{ fontSize: 20, color: '#1a73e8' }} />
                            <Typography
                              variant="subtitle1"
                              sx={{
                                fontSize: '16px',
                                fontWeight: 500,
                                color: '#202124',
                              }}
                            >
                              Bi-directional sync
                            </Typography>
                          </Box>

                          {/* Forward direction */}
                          <Box sx={{ mb: 2, pb: 2, borderBottom: '1px solid #f1f3f4' }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: '#202124',
                                mb: 1,
                              }}
                            >
                              {getCalendarDisplayName(forwardConfig.source_calendar_id)}
                              <Box component="span" sx={{ mx: 1, color: '#5f6368' }}>→</Box>
                              {getCalendarDisplayName(forwardConfig.dest_calendar_id)}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {forwardConfig.destination_color_id && CALENDAR_COLORS[forwardConfig.destination_color_id] && (
                                <Chip
                                  icon={
                                    <Circle
                                      sx={{
                                        fontSize: 12,
                                        color: `${CALENDAR_COLORS[forwardConfig.destination_color_id].color} !important`
                                      }}
                                    />
                                  }
                                  label={CALENDAR_COLORS[forwardConfig.destination_color_id].name}
                                  size="small"
                                  sx={{
                                    height: 24,
                                    fontSize: '12px',
                                    bgcolor: 'transparent',
                                    border: '1px solid #dadce0',
                                    color: '#5f6368',
                                  }}
                                />
                              )}
                              {forwardConfig.privacy_mode_enabled && (
                                <Chip
                                  icon={<Lock sx={{ fontSize: 14 }} />}
                                  label={`Privacy: "${forwardConfig.privacy_placeholder_text}"`}
                                  size="small"
                                  sx={{
                                    height: 24,
                                    fontSize: '12px',
                                    bgcolor: 'transparent',
                                    border: '1px solid #dadce0',
                                    color: '#5f6368',
                                  }}
                                />
                              )}
                            </Box>
                          </Box>

                          {/* Reverse direction */}
                          {reverseConfig && (
                            <Box sx={{ mb: 2 }}>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: '14px',
                                  color: '#202124',
                                  mb: 1,
                                }}
                              >
                                {getCalendarDisplayName(reverseConfig.source_calendar_id)}
                                <Box component="span" sx={{ mx: 1, color: '#5f6368' }}>→</Box>
                                {getCalendarDisplayName(reverseConfig.dest_calendar_id)}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                {reverseConfig.destination_color_id && CALENDAR_COLORS[reverseConfig.destination_color_id] && (
                                  <Chip
                                    icon={
                                      <Circle
                                        sx={{
                                          fontSize: 12,
                                          color: `${CALENDAR_COLORS[reverseConfig.destination_color_id].color} !important`
                                        }}
                                      />
                                    }
                                    label={CALENDAR_COLORS[reverseConfig.destination_color_id].name}
                                    size="small"
                                    sx={{
                                      height: 24,
                                      fontSize: '12px',
                                      bgcolor: 'transparent',
                                      border: '1px solid #dadce0',
                                      color: '#5f6368',
                                    }}
                                  />
                                )}
                                {reverseConfig.privacy_mode_enabled && (
                                  <Chip
                                    icon={<Lock sx={{ fontSize: 14 }} />}
                                    label={`Privacy: "${reverseConfig.privacy_placeholder_text}"`}
                                    size="small"
                                    sx={{
                                      height: 24,
                                      fontSize: '12px',
                                      bgcolor: 'transparent',
                                      border: '1px solid #dadce0',
                                      color: '#5f6368',
                                    }}
                                  />
                                )}
                              </Box>
                            </Box>
                          )}

                          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1 }}>
                            <Typography variant="caption" sx={{ color: '#5f6368', fontSize: '13px' }}>
                              {forwardConfig.sync_lookahead_days} days
                            </Typography>
                            {forwardConfig.last_synced_at && (
                              <Typography variant="caption" sx={{ color: '#5f6368', fontSize: '13px' }}>
                                Last synced {new Date(forwardConfig.last_synced_at).toLocaleDateString()}
                              </Typography>
                            )}
                          </Box>
                        </CardContent>

                        <CardActions sx={{ px: 3, pb: 2.5, pt: 0, justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              variant="contained"
                              size="small"
                              startIcon={<PlayArrow />}
                              onClick={() => handleTriggerSync(forwardConfig.id, true)}
                              disabled={syncingConfigId === forwardConfig.id}
                              sx={{
                                textTransform: 'none',
                                fontSize: '14px',
                                fontWeight: 500,
                                borderRadius: 2,
                                bgcolor: '#1a73e8',
                                '&:hover': { bgcolor: '#1765cc' },
                                '&:disabled': { bgcolor: '#dadce0' },
                              }}
                            >
                              {syncingConfigId === forwardConfig.id ? 'Syncing...' : 'Sync'}
                            </Button>
                            <Button
                              variant="text"
                              size="small"
                              startIcon={<History />}
                              onClick={() => handleViewHistory(forwardConfig.id)}
                              sx={{
                                textTransform: 'none',
                                fontSize: '14px',
                                fontWeight: 500,
                                borderRadius: 2,
                                color: '#5f6368',
                                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                              }}
                            >
                              History
                            </Button>
                          </Box>
                          <Button
                            variant="text"
                            size="small"
                            startIcon={<Delete />}
                            onClick={() => handleDeleteBidirectionalPair(forwardConfig.id, reverseConfig?.id || '')}
                            sx={{
                              textTransform: 'none',
                              fontSize: '14px',
                              fontWeight: 500,
                              borderRadius: 2,
                              color: '#d93025',
                              '&:hover': { bgcolor: 'rgba(217, 48, 37, 0.04)' },
                            }}
                          >
                            Delete
                          </Button>
                        </CardActions>
                      </Card>
                    );
                  })}

                  {/* One-way configs */}
                  {groupedConfigs.oneWay.map((config) => (
                    <Card
                      key={config.id}
                      elevation={0}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 3,
                        bgcolor: 'white',
                      }}
                    >
                      <CardContent sx={{ p: 3 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
                          <ArrowForward sx={{ fontSize: 20, color: '#5f6368' }} />
                          <Typography
                            variant="subtitle1"
                            sx={{
                              fontSize: '16px',
                              fontWeight: 500,
                              color: '#202124',
                            }}
                          >
                            One-way sync
                          </Typography>
                        </Box>

                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: '#202124',
                            }}
                          >
                            {getCalendarDisplayName(config.source_calendar_id)}
                            <Box component="span" sx={{ mx: 1, color: '#5f6368' }}>→</Box>
                            {getCalendarDisplayName(config.dest_calendar_id)}
                          </Typography>
                          <Chip
                            label={config.is_active ? 'Active' : 'Inactive'}
                            size="small"
                            sx={{
                              height: 24,
                              fontSize: '12px',
                              bgcolor: config.is_active ? '#e6f4ea' : '#f1f3f4',
                              color: config.is_active ? '#1e8e3e' : '#5f6368',
                              border: 'none',
                            }}
                          />
                        </Box>

                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
                          {config.destination_color_id && CALENDAR_COLORS[config.destination_color_id] && (
                            <Chip
                              icon={
                                <Circle
                                  sx={{
                                    fontSize: 12,
                                    color: `${CALENDAR_COLORS[config.destination_color_id].color} !important`
                                  }}
                                />
                              }
                              label={CALENDAR_COLORS[config.destination_color_id].name}
                              size="small"
                              sx={{
                                height: 24,
                                fontSize: '12px',
                                bgcolor: 'transparent',
                                border: '1px solid #dadce0',
                                color: '#5f6368',
                              }}
                            />
                          )}
                          {config.privacy_mode_enabled && (
                            <Chip
                              icon={<Lock sx={{ fontSize: 14 }} />}
                              label={`Privacy: "${config.privacy_placeholder_text}"`}
                              size="small"
                              sx={{
                                height: 24,
                                fontSize: '12px',
                                bgcolor: 'transparent',
                                border: '1px solid #dadce0',
                                color: '#5f6368',
                              }}
                            />
                          )}
                        </Box>

                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Typography variant="caption" sx={{ color: '#5f6368', fontSize: '13px' }}>
                            {config.sync_lookahead_days} days
                          </Typography>
                          {config.last_synced_at && (
                            <Typography variant="caption" sx={{ color: '#5f6368', fontSize: '13px' }}>
                              Last synced {new Date(config.last_synced_at).toLocaleDateString()}
                            </Typography>
                          )}
                        </Box>
                      </CardContent>

                      <CardActions sx={{ px: 3, pb: 2.5, pt: 0, justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={<PlayArrow />}
                            onClick={() => handleTriggerSync(config.id)}
                            disabled={syncingConfigId === config.id}
                            sx={{
                              textTransform: 'none',
                              fontSize: '14px',
                              fontWeight: 500,
                              borderRadius: 2,
                              bgcolor: '#1a73e8',
                              '&:hover': { bgcolor: '#1765cc' },
                              '&:disabled': { bgcolor: '#dadce0' },
                            }}
                          >
                            {syncingConfigId === config.id ? 'Syncing...' : 'Sync'}
                          </Button>
                          <Button
                            variant="text"
                            size="small"
                            startIcon={<History />}
                            onClick={() => handleViewHistory(config.id)}
                            sx={{
                              textTransform: 'none',
                              fontSize: '14px',
                              fontWeight: 500,
                              borderRadius: 2,
                              color: '#5f6368',
                              '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                            }}
                          >
                            History
                          </Button>
                        </Box>
                        <Button
                          variant="text"
                          size="small"
                          startIcon={<Delete />}
                          onClick={() => handleDeleteConfig(config.id)}
                          sx={{
                            textTransform: 'none',
                            fontSize: '14px',
                            fontWeight: 500,
                            borderRadius: 2,
                            color: '#d93025',
                            '&:hover': { bgcolor: 'rgba(217, 48, 37, 0.04)' },
                          }}
                        >
                          Delete
                        </Button>
                      </CardActions>
                    </Card>
                  ))}
                </Stack>
              </Box>
            )}

            {/* Empty state - show create button when no syncs exist */}
            {syncConfigs.length === 0 && oauthStatus?.source_connected && oauthStatus?.destination_connected && (
              <Box
                sx={{
                  textAlign: 'center',
                  py: 8,
                  px: 3,
                  bgcolor: 'white',
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 3,
                }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    fontSize: '18px',
                    fontWeight: 400,
                    color: '#202124',
                    mb: 1,
                  }}
                >
                  No syncs configured
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: '14px',
                    color: '#5f6368',
                    mb: 3,
                  }}
                >
                  Create your first sync to start syncing events between your connected accounts
                </Typography>
                <SyncConfigForm
                  onConfigCreated={() => {
                    fetchSyncConfigs();
                  }}
                />
              </Box>
            )}
          </Stack>
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

      {/* Confirmation Dialog */}
      <ConfirmDialog
        open={confirmDialogOpen}
        onClose={() => setConfirmDialogOpen(false)}
        onConfirm={confirmDialogConfig.onConfirm}
        title={confirmDialogConfig.title}
        message={confirmDialogConfig.message}
        confirmText="Delete"
        confirmColor="error"
        loading={deletingConfig}
      />
    </Box>
  );
}
