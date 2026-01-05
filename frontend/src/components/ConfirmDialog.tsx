import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
} from '@mui/material';
import { Close, Warning } from '@mui/icons-material';
import { StyledDialog, StyledIconButton, SecondaryButton, PrimaryButton, TypographyLabel } from './common';
import { APP_COLORS } from '../constants/colors';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  confirmColor?: 'error' | 'primary';
  loading?: boolean;
}

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  confirmColor = 'error',
  loading = false,
}: ConfirmDialogProps) {
  return (
    <StyledDialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle sx={{ pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Warning
              sx={{
                fontSize: 24,
                color: confirmColor === 'error' ? APP_COLORS.status.error : APP_COLORS.brand.primary,
              }}
            />
            <TypographyLabel
              sx={{
                fontSize: '18px',
                fontWeight: 400,
                letterSpacing: '-0.2px',
              }}
            >
              {title}
            </TypographyLabel>
          </Box>
          <StyledIconButton
            onClick={onClose}
            size="small"
            disabled={loading}
          >
            <Close fontSize="small" />
          </StyledIconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: 3, pb: 2 }}>
        <TypographyLabel
          variant="label"
          sx={{
            lineHeight: 1.6,
          }}
        >
          {message}
        </TypographyLabel>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3, pt: 0 }}>
        <SecondaryButton
          onClick={onClose}
          disabled={loading}
        >
          Cancel
        </SecondaryButton>
        <PrimaryButton
          onClick={onConfirm}
          disabled={loading}
          sx={{
            px: 3,
            bgcolor: confirmColor === 'error' ? APP_COLORS.status.error : APP_COLORS.brand.primary,
            '&:hover': {
              bgcolor: confirmColor === 'error' ? APP_COLORS.status.errorHover : APP_COLORS.brand.primaryHover,
            },
          }}
        >
          {loading ? 'Deleting...' : confirmText}
        </PrimaryButton>
      </DialogActions>
    </StyledDialog>
  );
}
