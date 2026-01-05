import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Box,
  Alert,
} from '@mui/material';
import { Google } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { oauthAPI } from '../services/api';
import { InfoCard, PrimaryButton, TypographyLabel } from '../components/common';
import { APP_COLORS } from '../constants/colors';

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
        bgcolor: APP_COLORS.surface.background,
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
          <InfoCard
            sx={{
              p: 5,
              width: '100%',
            }}
          >
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <TypographyLabel
                component="h1"
                sx={{
                  fontSize: '32px',
                  fontWeight: 400,
                  mb: 1,
                  letterSpacing: '-0.5px',
                }}
              >
                Calendar Sync
              </TypographyLabel>
              <TypographyLabel
                variant="label"
                sx={{
                  fontSize: '18px',
                  fontWeight: 400,
                  letterSpacing: '-0.2px',
                }}
              >
                Sign in with Google
              </TypographyLabel>
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
              <TypographyLabel
                variant="caption"
                sx={{
                  textAlign: 'center',
                  lineHeight: 1.6,
                  mb: 3,
                }}
              >
                Your Google account will become Account 1.
                <br />
                After signing in, you'll connect Account 2 and select which calendars to sync.
              </TypographyLabel>

              <PrimaryButton
                fullWidth
                startIcon={<Google />}
                onClick={handleGoogleLogin}
                disabled={loading}
                sx={{
                  py: 1.5,
                  mb: 2,
                }}
              >
                {loading ? 'Connecting...' : 'Sign in with Google'}
              </PrimaryButton>
            </Box>
          </InfoCard>
        </Box>
      </Container>
    </Box>
  );
}
