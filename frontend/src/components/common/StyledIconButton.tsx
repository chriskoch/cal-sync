import React from 'react';
import { IconButton, IconButtonProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface StyledIconButtonProps extends Omit<IconButtonProps, 'sx'> {
  sx?: SxProps;
}

const styles = {
  root: {
    color: APP_COLORS.text.secondary,
    '&:hover': { bgcolor: APP_COLORS.surface.hover },
  },
} as const;

/**
 * StyledIconButton - IconButton with standardized hover behavior
 *
 * @example
 * <StyledIconButton onClick={handleClose}>
 *   <Close />
 * </StyledIconButton>
 */
export const StyledIconButton: React.FC<StyledIconButtonProps> = ({ sx = {}, children, ...rest }) => (
  <IconButton
    sx={{
      ...styles.root,
      ...sx,
    }}
    {...rest}
  >
    {children}
  </IconButton>
);
