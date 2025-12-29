import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  IconButton,
} from '@mui/material';
import { Close, Warning } from '@mui/icons-material';

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
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        elevation: 0,
        sx: {
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
        },
      }}
    >
      <DialogTitle sx={{ pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Warning
              sx={{
                fontSize: 24,
                color: confirmColor === 'error' ? '#d93025' : '#1a73e8',
              }}
            />
            <Typography
              variant="h6"
              sx={{
                fontSize: '18px',
                fontWeight: 400,
                color: '#202124',
                letterSpacing: '-0.2px',
              }}
            >
              {title}
            </Typography>
          </Box>
          <IconButton
            onClick={onClose}
            size="small"
            disabled={loading}
            sx={{
              color: '#5f6368',
              '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
            }}
          >
            <Close fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: 3, pb: 2 }}>
        <Typography
          sx={{
            fontSize: '14px',
            color: '#5f6368',
            lineHeight: 1.6,
          }}
        >
          {message}
        </Typography>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3, pt: 0 }}>
        <Button
          onClick={onClose}
          disabled={loading}
          sx={{
            textTransform: 'none',
            fontSize: '14px',
            fontWeight: 500,
            borderRadius: 2,
            color: '#5f6368',
            '&:hover': {
              bgcolor: 'rgba(0, 0, 0, 0.04)',
            },
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          disabled={loading}
          sx={{
            textTransform: 'none',
            fontSize: '14px',
            fontWeight: 500,
            borderRadius: 2,
            px: 3,
            bgcolor: confirmColor === 'error' ? '#d93025' : '#1a73e8',
            '&:hover': {
              bgcolor: confirmColor === 'error' ? '#b3190f' : '#1765cc',
            },
            '&:disabled': {
              bgcolor: '#dadce0',
              color: '#5f6368',
            },
          }}
        >
          {loading ? 'Deleting...' : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
