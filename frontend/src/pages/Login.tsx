import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Box,
  Button,
  Typography,
  Card,
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
  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      localStorage.setItem('access_token', token);
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
      window.location.href = response.data.authorization_url;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to initiate Google login');
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#f8f9fa',
      }}
    >
      <Container maxWidth="sm">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Card
            elevation={0}
            sx={{
              p: 5,
              width: '100%',
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 3,
              bgcolor: 'white',
            }}
          >
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography
                component="h1"
                sx={{
                  fontSize: '32px',
                  fontWeight: 400,
                  color: '#202124',
                  mb: 1,
                  letterSpacing: '-0.5px',
                }}
              >
                Calendar Sync
              </Typography>
              <Typography
                variant="h6"
                sx={{
                  fontSize: '18px',
                  fontWeight: 400,
                  color: '#5f6368',
                  letterSpacing: '-0.2px',
                }}
              >
                Sign in with Google
              </Typography>
            </Box>

            {error && (
              <Alert
                severity="error"
                sx={{
                  mb: 3,
                  borderRadius: 2,
                }}
              >
                {error}
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <Typography
                variant="body2"
                sx={{
                  fontSize: '13px',
                  color: '#5f6368',
                  textAlign: 'center',
                  lineHeight: 1.6,
                  mb: 3,
                }}
              >
                Your Google account will become Account 1.
                <br />
                After signing in, you'll connect Account 2 and select which calendars to sync.
              </Typography>

              <Button
                variant="contained"
                fullWidth
                startIcon={<Google />}
                onClick={handleGoogleLogin}
                disabled={loading}
                sx={{
                  textTransform: 'none',
                  fontSize: '14px',
                  fontWeight: 500,
                  borderRadius: 2,
                  py: 1.5,
                  mb: 2,
                  bgcolor: '#1a73e8',
                  '&:hover': {
                    bgcolor: '#1765cc',
                  },
                  '&:disabled': {
                    bgcolor: '#dadce0',
                    color: '#5f6368',
                  },
                }}
              >
                {loading ? 'Connecting...' : 'Sign in with Google'}
              </Button>
            </Box>
          </Card>
        </Box>
      </Container>
    </Box>
  );
}
