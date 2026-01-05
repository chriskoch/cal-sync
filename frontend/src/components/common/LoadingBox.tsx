import React from 'react';
import { Box, CircularProgress, Typography, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface LoadingBoxProps {
  message?: string;
  size?: number;
  sx?: SxProps;
}

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    p: 3,
    bgcolor: APP_COLORS.surface.background,
    borderRadius: 2,
    border: `1px solid ${APP_COLORS.surface.border}`,
  },
  spinner: {
    color: APP_COLORS.brand.primary,
  },
  text: {
    fontSize: '14px',
    color: APP_COLORS.text.secondary,
    ml: 2,
  },
} as const;

/**
 * LoadingBox - Standardized loading state display
 *
 * @example
 * <LoadingBox message="Loading calendars..." />
 * <LoadingBox size={30} />
 */
export const LoadingBox: React.FC<LoadingBoxProps> = ({ message, size = 24, sx = {} }) => (
  <Box
    sx={{
      ...styles.container,
      ...sx,
    }}
  >
    <CircularProgress size={size} sx={styles.spinner} />
    {message && <Typography sx={styles.text}>{message}</Typography>}
  </Box>
);
