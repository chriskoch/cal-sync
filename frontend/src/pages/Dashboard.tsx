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
} from '@mui/material';
import { CheckCircle, Cancel, ExitToApp, PlayArrow, Refresh, Delete } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI, OAuthStatus, SyncConfig, syncAPI } from '../services/api';
import SyncConfigForm from '../components/SyncConfigForm';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
  const [syncConfigs, setSyncConfigs] = useState<SyncConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [syncingConfigId, setSyncingConfigId] = useState<string | null>(null);

  useEffect(() => {
    fetchOAuthStatus();
    fetchSyncConfigs();
  }, []);

  const fetchOAuthStatus = async () => {
    try {
      const response = await oauthAPI.getStatus();
      setOauthStatus(response.data);
    } catch (err: any) {
      setError('Failed to fetch OAuth status');
    } finally {
      setLoading(false);
    }
  };

  const fetchSyncConfigs = async () => {
    try {
      const response = await syncAPI.listConfigs();
      setSyncConfigs(response.data);
    } catch (err: any) {
      console.error('Failed to fetch sync configs:', err);
    }
  };

  const handleTriggerSync = async (configId: string) => {
    try {
      setSyncingConfigId(configId);
      setError('');
      setSuccess('');
      const response = await syncAPI.triggerSync(configId);

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to trigger sync');
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete sync configuration');
    }
  };

  const handleConnectAccount = async (accountType: 'source' | 'destination') => {
    try {
      const response = await oauthAPI.startOAuth(accountType);
      window.location.href = response.data.authorization_url;
    } catch (err: any) {
      setError(`Failed to initiate OAuth for ${accountType} account`);
    }
  };

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
          <Button color="inherit" onClick={logout} startIcon={<ExitToApp />}>
            Logout
          </Button>
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
            {/* Source Calendar Card */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    Source Calendar
                  </Typography>
                  <Typography color="text.secondary" gutterBottom>
                    The calendar you want to sync FROM
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

            {/* Destination Calendar Card */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    Destination Calendar
                  </Typography>
                  <Typography color="text.secondary" gutterBottom>
                    The calendar you want to sync TO
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
                    {syncConfigs.map((config) => (
                      <Grid item xs={12} key={config.id}>
                        <Card variant="outlined">
                          <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                              <Box>
                                <Typography variant="h6" gutterBottom>
                                  Sync Configuration
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Source Calendar: <strong>{config.source_calendar_id}</strong>
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Destination Calendar: <strong>{config.dest_calendar_id}</strong>
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                  Sync Lookahead: <strong>{config.sync_lookahead_days} days</strong>
                                </Typography>
                                {config.last_synced_at && (
                                  <Typography variant="body2" color="text.secondary">
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
                          <CardActions sx={{ justifyContent: 'space-between' }}>
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
                  onConfigCreated={(config: SyncConfig) => {
                    console.log('Sync config created:', config);
                    fetchSyncConfigs(); // Refresh the list
                  }}
                />
              </Grid>
            )}
          </Grid>
        )}
      </Container>
    </>
  );
}
