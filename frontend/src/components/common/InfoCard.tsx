import React from 'react';
import { Card, CardProps, SxProps } from '@mui/material';
import { APP_COLORS } from '../../constants/colors';

interface InfoCardProps extends Omit<CardProps, 'elevation' | 'variant' | 'sx'> {
  children: React.ReactNode;
  variant?: 'default' | 'highlighted' | 'bordered';
  sx?: SxProps;
}

const styles = {
  default: {
    border: '1px solid',
    borderColor: 'divider',
    borderRadius: 3,
    bgcolor: 'white',
    transition: 'all 0.2s ease',
    '&:hover': {
      boxShadow: '0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15)',
    },
  },
  highlighted: {
    border: `1px solid`,
    borderColor: APP_COLORS.brand.primary,
    borderRadius: 3,
    bgcolor: 'white',
    overflow: 'visible',
  },
  bordered: {
    border: `1px solid ${APP_COLORS.surface.border}`,
    borderRadius: 2,
    bgcolor: APP_COLORS.surface.background,
  },
} as const;

/**
 * InfoCard - Standardized card component with consistent styling
 *
 * @example
 * // Default variant with hover effect
 * <InfoCard>
 *   <CardContent>Content here</CardContent>
 * </InfoCard>
 *
 * // Highlighted variant (e.g., for bi-directional sync)
 * <InfoCard variant="highlighted">
 *   <CardContent>Important content</CardContent>
 * </InfoCard>
 *
 * // Bordered variant (e.g., for privacy settings)
 * <InfoCard variant="bordered">
 *   <CardContent>Settings content</CardContent>
 * </InfoCard>
 */
export const InfoCard: React.FC<InfoCardProps> = ({
  children,
  variant = 'default',
  sx = {},
  ...rest
}) => {
  let variantStyles = {};

  switch (variant) {
    case 'highlighted':
      variantStyles = styles.highlighted;
      break;
    case 'bordered':
      variantStyles = styles.bordered;
      break;
    default:
      variantStyles = styles.default;
  }

  return (
    <Card
      elevation={0}
      sx={{
        ...variantStyles,
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Card>
  );
};
