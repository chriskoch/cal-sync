import { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Grid,
  CardContent,
  CardActions,
  Alert,
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
  Schedule,
  DateRange,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI, OAuthStatus, SyncConfig, syncAPI, calendarsAPI, CalendarItem } from '../services/api';
import SyncConfigForm from '../components/SyncConfigForm';
import SyncHistoryDialog from '../components/SyncHistoryDialog';
import ConfirmDialog from '../components/ConfirmDialog';
import { CALENDAR_COLORS_MAP, APP_COLORS } from '../constants/colors';
import {
  StyledIconButton,
  PrimaryButton,
  SecondaryButton,
  OutlinedButton,
  DangerButton,
  InfoCard,
  SmallChip,
  TypographyLabel,
} from '../components/common';

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
  const [calendarColors, setCalendarColors] = useState<{ [key: string]: string }>({});

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
      const colorMap: { [key: string]: string } = {};

      // Fetch source calendars
      try {
        const sourceResponse = await calendarsAPI.listCalendars('source');
        sourceResponse.data.calendars.forEach((cal: CalendarItem) => {
          nameMap[cal.id] = cal.summary;
          if (cal.color_id) {
            colorMap[cal.id] = cal.color_id;
          }
        });
      } catch (err) {
        console.error('Failed to fetch source calendars:', err);
      }

      // Fetch destination calendars
      try {
        const destResponse = await calendarsAPI.listCalendars('destination');
        destResponse.data.calendars.forEach((cal: CalendarItem) => {
          nameMap[cal.id] = cal.summary;
          if (cal.color_id) {
            colorMap[cal.id] = cal.color_id;
          }
        });
      } catch (err) {
        console.error('Failed to fetch destination calendars:', err);
      }

      setCalendarNames(nameMap);
      setCalendarColors(colorMap);
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

          // Optimistically remove from UI
          setSyncConfigs(prevConfigs => prevConfigs.filter(c => c.id !== configId));

          setConfirmDialogOpen(false);
          setSuccess('Sync deleted successfully!');
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
          // Delete both configs (only delete reverse if it exists)
          await syncAPI.deleteConfig(forwardConfigId);
          if (reverseConfigId && reverseConfigId !== '') {
            await syncAPI.deleteConfig(reverseConfigId);
          }

          // Optimistically remove both from UI
          setSyncConfigs(prevConfigs =>
            prevConfigs.filter(c => c.id !== forwardConfigId && c.id !== reverseConfigId)
          );

          setConfirmDialogOpen(false);
          setSuccess('Bi-directional sync deleted successfully!');
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
        // Use consistent key: the smaller of the two IDs (lexicographically)
        // This ensures both configs in a pair use the same key
        const pairId = config.paired_config_id && config.paired_config_id < config.id
          ? config.paired_config_id
          : config.id;

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
      bgcolor: APP_COLORS.surface.background,
    }}>
      {/* Header */}
      <Box
        component="header"
        sx={{
          bgcolor: APP_COLORS.surface.paper,
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
                color: APP_COLORS.text.primary,
                letterSpacing: '-0.2px',
              }}
            >
              Calendar Sync
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  color: APP_COLORS.text.secondary,
                  fontSize: '14px',
                }}
              >
                {user?.email}
              </Typography>
              <StyledIconButton
                onClick={handleUserMenuOpen}
                size="small"
              >
                <AccountCircle />
              </StyledIconButton>
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
          <Typography sx={{ color: APP_COLORS.text.secondary, py: 4, textAlign: 'center' }}>
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
                  color: APP_COLORS.text.primary,
                  mb: 2,
                  letterSpacing: '-0.3px',
                }}
              >
                Accounts
              </Typography>
              <Grid container spacing={2}>
                {/* Business Calendar */}
                <Grid item xs={12} md={6}>
                  <InfoCard>
                    <CardContent sx={{ p: 3 }}>
                      <TypographyLabel
                        variant="subheading"
                        sx={{ mb: 0.5 }}
                      >
                        Account 1
                      </TypographyLabel>
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '14px',
                          color: APP_COLORS.text.secondary,
                          mb: 2.5,
                        }}
                      >
                        Your first connected Google account
                      </Typography>

                      {oauthStatus?.source_connected ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <CheckCircle sx={{ fontSize: 20, color: APP_COLORS.status.success }} />
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: APP_COLORS.text.primary,
                                fontWeight: 500,
                              }}
                            >
                              Connected
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '13px',
                                color: APP_COLORS.text.secondary,
                              }}
                            >
                              {oauthStatus.source_email}
                            </Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Cancel sx={{ fontSize: 20, color: APP_COLORS.status.error }} />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: APP_COLORS.text.secondary,
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
                          <OutlinedButton
                            onClick={() => handleConnectAccount('source')}
                          >
                            Reconnect
                          </OutlinedButton>
                        </Tooltip>
                      ) : (
                        <PrimaryButton
                          onClick={() => handleConnectAccount('source')}
                        >
                          Connect account
                        </PrimaryButton>
                      )}
                    </CardActions>
                  </InfoCard>
                </Grid>

                {/* Private Calendar */}
                <Grid item xs={12} md={6}>
                  <InfoCard>
                    <CardContent sx={{ p: 3 }}>
                      <TypographyLabel
                        variant="subheading"
                        sx={{ mb: 0.5 }}
                      >
                        Account 2
                      </TypographyLabel>
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '14px',
                          color: APP_COLORS.text.secondary,
                          mb: 2.5,
                        }}
                      >
                        Your second connected Google account
                      </Typography>

                      {oauthStatus?.destination_connected ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <CheckCircle sx={{ fontSize: 20, color: APP_COLORS.status.success }} />
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: APP_COLORS.text.primary,
                                fontWeight: 500,
                              }}
                            >
                              Connected
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '13px',
                                color: APP_COLORS.text.secondary,
                              }}
                            >
                              {oauthStatus.destination_email}
                            </Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Cancel sx={{ fontSize: 20, color: APP_COLORS.status.error }} />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: APP_COLORS.text.secondary,
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
                          <OutlinedButton
                            onClick={() => handleConnectAccount('destination')}
                          >
                            Reconnect
                          </OutlinedButton>
                        </Tooltip>
                      ) : (
                        <PrimaryButton
                          onClick={() => handleConnectAccount('destination')}
                        >
                          Connect account
                        </PrimaryButton>
                      )}
                    </CardActions>
                  </InfoCard>
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
                      color: APP_COLORS.text.primary,
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
                    <StyledIconButton
                      size="small"
                      onClick={fetchSyncConfigs}
                    >
                      <Refresh fontSize="small" />
                    </StyledIconButton>
                  </Box>
                </Box>

                <Stack spacing={2}>
                  {/* Bi-directional configs */}
                  {Object.entries(groupedConfigs.bidirectional).map(([pairId, configs]) => {
                    const forwardConfig = configs.find(c => c.sync_direction === 'bidirectional_a_to_b');
                    const reverseConfig = configs.find(c => c.sync_direction === 'bidirectional_b_to_a');

                    if (!forwardConfig) return null;

                    return (
                      <InfoCard
                        key={pairId}
                        sx={{
                          borderColor: APP_COLORS.brand.primary,
                        }}
                      >
                        <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
                            <SwapHoriz sx={{ fontSize: 20, color: APP_COLORS.brand.primary }} />
                            <TypographyLabel variant="subheading">
                              Bi-directional sync
                            </TypographyLabel>
                          </Box>

                          {/* Forward direction */}
                          <Box sx={{ mb: 2, pb: 2, borderBottom: `1px solid ${APP_COLORS.surface.borderLight}` }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: APP_COLORS.text.primary,
                                mb: 1,
                                fontWeight: 500,
                              }}
                            >
                              {getCalendarDisplayName(forwardConfig.source_calendar_id)}
                              <Box component="span" sx={{ mx: 1, color: APP_COLORS.text.secondary }}>→</Box>
                              {getCalendarDisplayName(forwardConfig.dest_calendar_id)}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {(() => {
                                // If destination color is set, show it
                                if (forwardConfig.destination_color_id && CALENDAR_COLORS_MAP[forwardConfig.destination_color_id]) {
                                  return (
                                    <SmallChip
                                      variant="outlined"
                                      icon={
                                        <Circle
                                          sx={{
                                            fontSize: 12,
                                            color: `${CALENDAR_COLORS_MAP[forwardConfig.destination_color_id].color} !important`
                                          }}
                                        />
                                      }
                                      label={CALENDAR_COLORS_MAP[forwardConfig.destination_color_id].name}
                                    />
                                  );
                                }

                                // Otherwise, show source calendar color if available
                                const sourceColorId = calendarColors[forwardConfig.source_calendar_id];
                                if (sourceColorId) {
                                  // Calendar colors 12-24 aren't valid event colors, map to Lavender (1)
                                  const eventColorId = CALENDAR_COLORS_MAP[sourceColorId] ? sourceColorId : '1';
                                  return (
                                    <SmallChip
                                      variant="outlined"
                                      icon={
                                        <Circle
                                          sx={{
                                            fontSize: 12,
                                            color: `${CALENDAR_COLORS_MAP[eventColorId].color} !important`
                                          }}
                                        />
                                      }
                                      label={`${CALENDAR_COLORS_MAP[eventColorId].name} (source)`}
                                      sx={{ fontStyle: 'italic' }}
                                    />
                                  );
                                }

                                // Fallback to generic "Same as source"
                                return (
                                  <SmallChip
                                    variant="outlined"
                                    icon={<SwapHoriz sx={{ fontSize: 14 }} />}
                                    label="Same as source"
                                    sx={{ fontStyle: 'italic' }}
                                  />
                                );
                              })()}
                              {forwardConfig.privacy_mode_enabled && (
                                <SmallChip
                                  variant="outlined"
                                  icon={<Lock sx={{ fontSize: 14 }} />}
                                  label={`Privacy: "${forwardConfig.privacy_placeholder_text || 'Personal appointment'}"`}
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
                                  color: APP_COLORS.text.primary,
                                  mb: 1,
                                  fontWeight: 500,
                                }}
                              >
                                {getCalendarDisplayName(reverseConfig.source_calendar_id)}
                                <Box component="span" sx={{ mx: 1, color: APP_COLORS.text.secondary }}>→</Box>
                                {getCalendarDisplayName(reverseConfig.dest_calendar_id)}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                {(() => {
                                  // If destination color is set, show it
                                  if (reverseConfig.destination_color_id && CALENDAR_COLORS_MAP[reverseConfig.destination_color_id]) {
                                    return (
                                      <SmallChip
                                        variant="outlined"
                                        icon={
                                          <Circle
                                            sx={{
                                              fontSize: 12,
                                              color: `${CALENDAR_COLORS_MAP[reverseConfig.destination_color_id].color} !important`
                                            }}
                                          />
                                        }
                                        label={CALENDAR_COLORS_MAP[reverseConfig.destination_color_id].name}
                                      />
                                    );
                                  }

                                  // Otherwise, show source calendar color if available
                                  const sourceColorId = calendarColors[reverseConfig.source_calendar_id];
                                  if (sourceColorId) {
                                    // Calendar colors 12-24 aren't valid event colors, map to Lavender (1)
                                    const eventColorId = CALENDAR_COLORS_MAP[sourceColorId] ? sourceColorId : '1';
                                    return (
                                      <SmallChip
                                        variant="outlined"
                                        icon={
                                          <Circle
                                            sx={{
                                              fontSize: 12,
                                              color: `${CALENDAR_COLORS_MAP[eventColorId].color} !important`
                                            }}
                                          />
                                        }
                                        label={`${CALENDAR_COLORS_MAP[eventColorId].name} (source)`}
                                        sx={{ fontStyle: 'italic' }}
                                      />
                                    );
                                  }

                                  // Fallback to generic "Same as source"
                                  return (
                                    <SmallChip
                                      variant="outlined"
                                      icon={<SwapHoriz sx={{ fontSize: 14 }} />}
                                      label="Same as source"
                                      sx={{ fontStyle: 'italic' }}
                                    />
                                  );
                                })()}
                                {reverseConfig.privacy_mode_enabled && (
                                  <SmallChip
                                    variant="outlined"
                                    icon={<Lock sx={{ fontSize: 14 }} />}
                                    label={`Privacy: "${reverseConfig.privacy_placeholder_text || 'Personal appointment'}"`}
                                  />
                                )}
                              </Box>
                            </Box>
                          )}

                          {/* General settings */}
                          <Box sx={{ mt: 2.5, pt: 2, borderTop: `1px solid ${APP_COLORS.surface.borderLight}` }}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontSize: '14px',
                                color: APP_COLORS.text.primary,
                                mb: 1,
                                fontWeight: 500,
                              }}
                            >
                              Settings
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                              <SmallChip
                                variant="outlined"
                                icon={<DateRange sx={{ fontSize: 14 }} />}
                                label={`${forwardConfig.sync_lookahead_days} days`}
                              />
                              {forwardConfig.last_synced_at && (
                                <Typography variant="caption" sx={{ color: APP_COLORS.text.secondary, fontSize: '13px' }}>
                                  Last synced {new Date(forwardConfig.last_synced_at).toLocaleDateString()}
                                </Typography>
                              )}
                              {forwardConfig.auto_sync_enabled && (
                                <SmallChip
                                  variant="outlined"
                                  icon={<Schedule sx={{ fontSize: 14 }} />}
                                  label={`Auto: ${forwardConfig.auto_sync_cron} (${forwardConfig.auto_sync_timezone})`}
                                />
                              )}
                            </Box>
                          </Box>
                        </CardContent>

                        <CardActions sx={{ px: 3, pb: 2.5, pt: 0, justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <PrimaryButton
                              size="small"
                              startIcon={<PlayArrow />}
                              onClick={() => handleTriggerSync(forwardConfig.id, true)}
                              disabled={syncingConfigId === forwardConfig.id}
                            >
                              {syncingConfigId === forwardConfig.id ? 'Syncing...' : 'Sync'}
                            </PrimaryButton>
                            <SecondaryButton
                              size="small"
                              startIcon={<History />}
                              onClick={() => handleViewHistory(forwardConfig.id)}
                            >
                              History
                            </SecondaryButton>
                          </Box>
                          <DangerButton
                            size="small"
                            startIcon={<Delete />}
                            onClick={() => handleDeleteBidirectionalPair(forwardConfig.id, reverseConfig?.id || '')}
                          >
                            Delete
                          </DangerButton>
                        </CardActions>
                      </InfoCard>
                    );
                  })}

                  {/* One-way configs */}
                  {groupedConfigs.oneWay.map((config) => (
                    <InfoCard key={config.id}>
                      <CardContent sx={{ p: 3 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
                          <ArrowForward sx={{ fontSize: 20, color: APP_COLORS.text.secondary }} />
                          <TypographyLabel variant="subheading">
                            One-way sync
                          </TypographyLabel>
                        </Box>

                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '14px',
                              color: APP_COLORS.text.primary,
                              fontWeight: 500,
                            }}
                          >
                            {getCalendarDisplayName(config.source_calendar_id)}
                            <Box component="span" sx={{ mx: 1, color: APP_COLORS.text.secondary }}>→</Box>
                            {getCalendarDisplayName(config.dest_calendar_id)}
                          </Typography>
                          <SmallChip
                            label={config.is_active ? 'Active' : 'Inactive'}
                            variant={config.is_active ? 'status-success' : 'status-inactive'}
                          />
                        </Box>

                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
                          {(() => {
                            // If destination color is set, show it
                            if (config.destination_color_id && CALENDAR_COLORS_MAP[config.destination_color_id]) {
                              return (
                                <SmallChip
                                  variant="outlined"
                                  icon={
                                    <Circle
                                      sx={{
                                        fontSize: 12,
                                        color: `${CALENDAR_COLORS_MAP[config.destination_color_id].color} !important`
                                      }}
                                    />
                                  }
                                  label={CALENDAR_COLORS_MAP[config.destination_color_id].name}
                                />
                              );
                            }

                            // Otherwise, show source calendar color if available
                            const sourceColorId = calendarColors[config.source_calendar_id];
                            if (sourceColorId) {
                              // Calendar colors 12-24 aren't valid event colors, map to Lavender (1)
                              const eventColorId = CALENDAR_COLORS_MAP[sourceColorId] ? sourceColorId : '1';
                              return (
                                <SmallChip
                                  variant="outlined"
                                  icon={
                                    <Circle
                                      sx={{
                                        fontSize: 12,
                                        color: `${CALENDAR_COLORS_MAP[eventColorId].color} !important`
                                      }}
                                    />
                                  }
                                  label={`${CALENDAR_COLORS_MAP[eventColorId].name} (source)`}
                                  sx={{ fontStyle: 'italic' }}
                                />
                              );
                            }

                            // Fallback to generic "Same as source"
                            return (
                              <SmallChip
                                variant="outlined"
                                icon={<SwapHoriz sx={{ fontSize: 14 }} />}
                                label="Same as source"
                                sx={{ fontStyle: 'italic' }}
                              />
                            );
                          })()}
                          {config.privacy_mode_enabled && (
                            <SmallChip
                              variant="outlined"
                              icon={<Lock sx={{ fontSize: 14 }} />}
                              label={`Privacy: "${config.privacy_placeholder_text || 'Personal appointment'}"`}
                            />
                          )}
                        </Box>

                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                          <SmallChip
                            variant="outlined"
                            icon={<DateRange sx={{ fontSize: 14 }} />}
                            label={`${config.sync_lookahead_days} days`}
                          />
                          {config.last_synced_at && (
                            <Typography variant="caption" sx={{ color: APP_COLORS.text.secondary, fontSize: '13px' }}>
                              Last synced {new Date(config.last_synced_at).toLocaleDateString()}
                            </Typography>
                          )}
                          {config.auto_sync_enabled && (
                            <SmallChip
                              variant="outlined"
                              icon={<Schedule sx={{ fontSize: 14 }} />}
                              label={`Auto: ${config.auto_sync_cron} (${config.auto_sync_timezone})`}
                            />
                          )}
                        </Box>
                      </CardContent>

                      <CardActions sx={{ px: 3, pb: 2.5, pt: 0, justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <PrimaryButton
                            size="small"
                            startIcon={<PlayArrow />}
                            onClick={() => handleTriggerSync(config.id)}
                            disabled={syncingConfigId === config.id}
                          >
                            {syncingConfigId === config.id ? 'Syncing...' : 'Sync'}
                          </PrimaryButton>
                          <SecondaryButton
                            size="small"
                            startIcon={<History />}
                            onClick={() => handleViewHistory(config.id)}
                          >
                            History
                          </SecondaryButton>
                        </Box>
                        <DangerButton
                          size="small"
                          startIcon={<Delete />}
                          onClick={() => handleDeleteConfig(config.id)}
                        >
                          Delete
                        </DangerButton>
                      </CardActions>
                    </InfoCard>
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
                  bgcolor: APP_COLORS.surface.paper,
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
                    color: APP_COLORS.text.primary,
                    mb: 1,
                  }}
                >
                  No syncs configured
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: '14px',
                    color: APP_COLORS.text.secondary,
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
