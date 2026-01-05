import React from 'react';
import { Chip, ChipProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface SmallChipProps extends Omit<ChipProps, 'variant' | 'sx'> {
  label: string | number;
  icon?: React.ReactElement;
  variant?: 'default' | 'outlined' | 'status-success' | 'status-error' | 'status-running' | 'status-inactive';
  sx?: SxProps;
}

const styles = {
  base: {
    height: 24,
    fontSize: '12px',
    border: 'none',
  },
  outlined: {
    bgcolor: 'transparent',
    border: `1px solid ${APP_COLORS.surface.border}`,
    color: APP_COLORS.text.secondary,
  },
  statusSuccess: {
    bgcolor: APP_COLORS.status.successBg,
    color: APP_COLORS.status.success,
  },
  statusError: {
    bgcolor: APP_COLORS.status.errorBg,
    color: APP_COLORS.status.error,
  },
  statusRunning: {
    bgcolor: APP_COLORS.status.infoBg,
    color: APP_COLORS.status.info,
  },
  statusInactive: {
    bgcolor: APP_COLORS.surface.borderLight,
    color: APP_COLORS.text.secondary,
  },
} as const;

/**
 * SmallChip component - standardized chip styling used throughout the application
 *
 * @example
 * // Outlined variant (default for most use cases)
 * <SmallChip variant="outlined" label="90 days" />
 *
 * // Status variants
 * <SmallChip variant="status-success" icon={<CheckCircle />} label="Success" />
 * <SmallChip variant="status-error" icon={<ErrorIcon />} label="Failed" />
 *
 * // With custom styles
 * <SmallChip variant="outlined" label="Custom" sx={{ minWidth: 100 }} />
 */
export const SmallChip: React.FC<SmallChipProps> = ({
  label,
  icon,
  variant = 'default',
  sx = {},
  ...rest
}) => {
  let variantStyles = {};

  switch (variant) {
    case 'outlined':
      variantStyles = styles.outlined;
      break;
    case 'status-success':
      variantStyles = styles.statusSuccess;
      break;
    case 'status-error':
      variantStyles = styles.statusError;
      break;
    case 'status-running':
      variantStyles = styles.statusRunning;
      break;
    case 'status-inactive':
      variantStyles = styles.statusInactive;
      break;
    default:
      variantStyles = {};
  }

  return (
    <Chip
      label={label}
      icon={icon}
      sx={{
        ...styles.base,
        ...variantStyles,
        ...sx,
      }}
      {...rest}
    />
  );
};
