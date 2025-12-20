import { useState, useEffect } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Box,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  Paper,
} from '@mui/material';
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';
import { useAuth } from '../context/AuthContext';
import { getLoginErrorMessage } from '../utils/errorMessages';

const LOGIN_FAILURES_KEY = 'login_failures';

interface LoginFailures {
  [email: string]: {
    count: number;
    lastAttempt: string;
  };
}

function getLoginFailureCount(email: string): number {
  const stored = localStorage.getItem(LOGIN_FAILURES_KEY);
  if (!stored) return 0;

  try {
    const failures: LoginFailures = JSON.parse(stored);
    const failure = failures[email];

    if (!failure) return 0;

    // Check if failure is older than 1 hour
    const lastAttempt = new Date(failure.lastAttempt);
    const hourAgo = new Date(Date.now() - 60 * 60 * 1000);

    if (lastAttempt < hourAgo) {
      // Expired, remove it
      delete failures[email];
      localStorage.setItem(LOGIN_FAILURES_KEY, JSON.stringify(failures));
      return 0;
    }

    return failure.count;
  } catch {
    return 0;
  }
}

function recordLoginFailure(email: string) {
  const stored = localStorage.getItem(LOGIN_FAILURES_KEY);
  const failures: LoginFailures = stored ? JSON.parse(stored) : {};

  failures[email] = {
    count: (failures[email]?.count || 0) + 1,
    lastAttempt: new Date().toISOString(),
  };

  localStorage.setItem(LOGIN_FAILURES_KEY, JSON.stringify(failures));
}

function resetLoginFailures(email: string) {
  const stored = localStorage.getItem(LOGIN_FAILURES_KEY);
  if (!stored) return;

  try {
    const failures: LoginFailures = JSON.parse(stored);
    delete failures[email];
    localStorage.setItem(LOGIN_FAILURES_KEY, JSON.stringify(failures));
  } catch {
    // Ignore errors
  }
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [failureCount, setFailureCount] = useState(0);
  const { login } = useAuth();
  const { executeRecaptcha } = useGoogleReCaptcha();
  const navigate = useNavigate();

  useEffect(() => {
    // Update failure count when email changes
    if (email) {
      setFailureCount(getLoginFailureCount(email));
    }
  }, [email]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let recaptchaToken: string | undefined;

      // Generate reCAPTCHA token if needed (after 3 failures)
      if (failureCount >= 3) {
        if (!executeRecaptcha) {
          setError('reCAPTCHA not ready. Please try again.');
          setLoading(false);
          return;
        }

        recaptchaToken = await executeRecaptcha('login');
      }

      await login(email, password, recaptchaToken);

      // Successful login - reset failures
      resetLoginFailures(email);

      navigate('/dashboard');
    } catch (err: any) {
      // Record failed attempt
      recordLoginFailure(email);
      setFailureCount(getLoginFailureCount(email));

      setError(getLoginErrorMessage(err));
    } finally {
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
            Sign in
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {failureCount >= 3 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Multiple failed login attempts detected. reCAPTCHA verification required.
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
            <Box sx={{ textAlign: 'center' }}>
              <Link component={RouterLink} to="/register" variant="body2">
                Don't have an account? Sign Up
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
