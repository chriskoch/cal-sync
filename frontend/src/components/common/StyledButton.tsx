import React from 'react';
import { Button, ButtonProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

// Base button props without variant (we control variant internally)
interface BaseButtonProps extends Omit<ButtonProps, 'variant' | 'sx'> {
  sx?: SxProps;
}

const styles = {
  base: {
    textTransform: 'none',
    fontSize: '14px',
    fontWeight: 500,
    borderRadius: 2,
  },
  primary: {
    bgcolor: APP_COLORS.brand.primary,
    '&:hover': { bgcolor: APP_COLORS.brand.primaryHover },
    '&:disabled': { bgcolor: APP_COLORS.disabled.bg, color: APP_COLORS.disabled.text },
  },
  secondary: {
    color: APP_COLORS.text.secondary,
    '&:hover': { bgcolor: APP_COLORS.surface.hover },
  },
  outlined: {
    borderColor: APP_COLORS.surface.border,
    color: APP_COLORS.brand.secondary,
    '&:hover': {
      borderColor: APP_COLORS.brand.secondary,
      bgcolor: APP_COLORS.surface.hoverBlue,
    },
  },
  danger: {
    color: APP_COLORS.status.error,
    '&:hover': { bgcolor: APP_COLORS.surface.hoverRed },
  },
} as const;

/**
 * PrimaryButton - Contained button with primary brand color
 *
 * @example
 * <PrimaryButton onClick={handleClick}>Save</PrimaryButton>
 * <PrimaryButton startIcon={<Add />} disabled>Add Item</PrimaryButton>
 */
export const PrimaryButton: React.FC<BaseButtonProps> = ({ sx = {}, children, ...rest }) => (
  <Button
    variant="contained"
    sx={{
      ...styles.base,
      ...styles.primary,
      ...sx,
    }}
    {...rest}
  >
    {children}
  </Button>
);

/**
 * SecondaryButton - Text button with secondary styling
 *
 * @example
 * <SecondaryButton onClick={handleCancel}>Cancel</SecondaryButton>
 * <SecondaryButton startIcon={<History />}>View History</SecondaryButton>
 */
export const SecondaryButton: React.FC<BaseButtonProps> = ({ sx = {}, children, ...rest }) => (
  <Button
    variant="text"
    sx={{
      ...styles.base,
      ...styles.secondary,
      ...sx,
    }}
    {...rest}
  >
    {children}
  </Button>
);

/**
 * OutlinedButton - Outlined button with brand color
 *
 * @example
 * <OutlinedButton onClick={handleReconnect}>Reconnect</OutlinedButton>
 */
export const OutlinedButton: React.FC<BaseButtonProps> = ({ sx = {}, children, ...rest }) => (
  <Button
    variant="outlined"
    sx={{
      ...styles.base,
      ...styles.outlined,
      ...sx,
    }}
    {...rest}
  >
    {children}
  </Button>
);

/**
 * DangerButton - Text button with error/danger styling
 *
 * @example
 * <DangerButton startIcon={<Delete />} onClick={handleDelete}>Delete</DangerButton>
 */
export const DangerButton: React.FC<BaseButtonProps> = ({ sx = {}, children, ...rest }) => (
  <Button
    variant="text"
    sx={{
      ...styles.base,
      ...styles.danger,
      ...sx,
    }}
    {...rest}
  >
    {children}
  </Button>
);
