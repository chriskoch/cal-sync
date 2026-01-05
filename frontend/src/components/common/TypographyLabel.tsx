import React from 'react';
import { Typography, TypographyProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface TypographyLabelProps extends Omit<TypographyProps, 'variant' | 'sx'> {
  children: React.ReactNode;
  variant?: 'heading' | 'subheading' | 'label' | 'caption' | 'body';
  sx?: SxProps;
}

const styles = {
  heading: {
    fontSize: '24px',
    fontWeight: 400,
    color: APP_COLORS.text.primary,
    letterSpacing: '-0.3px',
  },
  subheading: {
    fontSize: '16px',
    fontWeight: 500,
    color: APP_COLORS.text.primary,
  },
  label: {
    fontSize: '14px',
    color: APP_COLORS.text.secondary,
  },
  caption: {
    fontSize: '13px',
    color: APP_COLORS.text.secondary,
  },
  body: {
    fontSize: '14px',
    color: APP_COLORS.text.primary,
  },
} as const;

/**
 * TypographyLabel - Typography component with standardized text styling
 *
 * @example
 * <TypographyLabel variant="heading">Page Title</TypographyLabel>
 * <TypographyLabel variant="label">Field label</TypographyLabel>
 * <TypographyLabel variant="caption">Helper text</TypographyLabel>
 */
export const TypographyLabel: React.FC<TypographyLabelProps> = ({
  children,
  variant = 'body',
  sx = {},
  ...rest
}) => {
  let variantStyles = {};

  switch (variant) {
    case 'heading':
      variantStyles = styles.heading;
      break;
    case 'subheading':
      variantStyles = styles.subheading;
      break;
    case 'label':
      variantStyles = styles.label;
      break;
    case 'caption':
      variantStyles = styles.caption;
      break;
    default:
      variantStyles = styles.body;
  }

  return (
    <Typography
      sx={{
        ...variantStyles,
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Typography>
  );
};
