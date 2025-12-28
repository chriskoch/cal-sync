import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Box,
  Button,
  Typography,
  Paper,
  Alert,
} from '@mui/material';
import { Google } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI } from '../services/api';

export default function Login() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Check if we have a token from OAuth callback
  // Note: This is also handled in AuthContext, but we keep this as a backup
  // The token should be extracted by AuthContext before reaching this component
  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      // Store token - AuthContext will handle authentication and redirect
      localStorage.setItem('access_token', token);
      // Trigger a page reload to let AuthContext pick up the token
      window.location.href = '/dashboard';
    }
  }, [searchParams]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);

    try {
      const response = await oauthAPI.startOAuth('register');
      // Redirect to Google OAuth
      window.location.href = response.data.authorization_url;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to initiate Google login');
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Calendar Sync
          </Typography>
          <Typography variant="h5" align="center" gutterBottom>
            Sign in with Google
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Button
              variant="contained"
              fullWidth
              startIcon={<Google />}
              onClick={handleGoogleLogin}
              disabled={loading}
              sx={{ mb: 2, py: 1.5 }}
            >
              {loading ? 'Connecting...' : 'Sign in with Google'}
            </Button>
            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 2 }}>
              By signing in, you agree to sync your Google Calendar events.
              Your Google account will be used as the from calendar.
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
