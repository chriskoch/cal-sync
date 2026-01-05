import React from 'react';
import { TextField, TextFieldProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface StyledTextFieldProps extends Omit<TextFieldProps, 'sx'> {
  sx?: SxProps;
}

const styles = {
  root: {
    '& .MuiOutlinedInput-root': {
      '& fieldset': {
        borderColor: APP_COLORS.surface.border,
      },
      '&:hover fieldset': {
        borderColor: APP_COLORS.brand.secondary,
      },
      '&.Mui-focused fieldset': {
        borderColor: APP_COLORS.brand.primary,
      },
    },
  },
} as const;

/**
 * StyledTextField - TextField with standardized border styling
 *
 * @example
 * <StyledTextField
 *   label="Email"
 *   value={email}
 *   onChange={handleChange}
 *   fullWidth
 * />
 */
export const StyledTextField: React.FC<StyledTextFieldProps> = ({ sx = {}, ...rest }) => (
  <TextField
    sx={{
      ...styles.root,
      ...sx,
    }}
    {...rest}
  />
);
