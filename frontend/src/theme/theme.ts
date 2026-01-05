import { createTheme } from '@mui/material/styles';
import { APP_COLORS } from '../constants/colors';

export const theme = createTheme({
  palette: {
    primary: {
      main: APP_COLORS.brand.primary,
      dark: APP_COLORS.brand.primaryHover,
    },
    secondary: {
      main: APP_COLORS.brand.secondary,
    },
    error: {
      main: APP_COLORS.status.error,
      light: APP_COLORS.status.errorBg,
    },
    success: {
      main: APP_COLORS.status.success,
      light: APP_COLORS.status.successBg,
    },
    text: {
      primary: APP_COLORS.text.primary,
      secondary: APP_COLORS.text.secondary,
    },
    divider: APP_COLORS.surface.border,
    background: {
      default: APP_COLORS.surface.background,
      paper: APP_COLORS.surface.paper,
    },
  },

  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',

    // Custom variants matching app patterns
    h1: {
      fontSize: '32px',
      fontWeight: 400,
      letterSpacing: '-0.5px',
    },
    h2: {
      fontSize: '24px',
      fontWeight: 400,
      letterSpacing: '-0.3px',
    },
    h3: {
      fontSize: '20px',
      fontWeight: 400,
      letterSpacing: '-0.2px',
    },
    h4: {
      fontSize: '18px',
      fontWeight: 400,
      letterSpacing: '-0.2px',
    },
    subtitle1: {
      fontSize: '16px',
      fontWeight: 500,
    },
    subtitle2: {
      fontSize: '14px',
      fontWeight: 500,
    },
    body1: {
      fontSize: '14px',
    },
    body2: {
      fontSize: '13px',
    },
    caption: {
      fontSize: '12px',
    },
  },

  spacing: 8, // Default MUI spacing (8px base unit)

  shape: {
    borderRadius: 8, // Default for most components
  },

  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      defaultProps: {
        elevation: 0,
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
        },
      },
    },
  },
});
