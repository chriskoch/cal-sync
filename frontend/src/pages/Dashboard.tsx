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
} from '@mui/material';
import { CheckCircle, Cancel, ExitToApp } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI, OAuthStatus } from '../services/api';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchOAuthStatus();
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
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
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

            {/* Next Steps Card */}
            {oauthStatus?.source_connected && oauthStatus?.destination_connected && (
              <Grid item xs={12}>
                <Paper sx={{ p: 3, bgcolor: 'success.light' }}>
                  <Typography variant="h6" gutterBottom>
                    Next Steps
                  </Typography>
                  <Typography>
                    Both accounts are connected! You can now select calendars and create sync configurations.
                  </Typography>
                  <Button variant="contained" sx={{ mt: 2 }}>
                    Set Up Sync
                  </Button>
                </Paper>
              </Grid>
            )}
          </Grid>
        )}
      </Container>
    </>
  );
}
