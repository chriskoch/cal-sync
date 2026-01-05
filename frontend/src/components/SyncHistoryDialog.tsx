import { useState, useEffect } from 'react';
import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box,
  CircularProgress,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, History, Close, Refresh } from '@mui/icons-material';
import { syncAPI, SyncLog } from '../services/api';
import { StyledDialog, StyledIconButton, SecondaryButton, SmallChip, TypographyLabel } from './common';
import { APP_COLORS } from '../constants/colors';

interface SyncHistoryDialogProps {
  open: boolean;
  onClose: () => void;
  configId: string;
}

export default function SyncHistoryDialog({ open, onClose, configId }: SyncHistoryDialogProps) {
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await syncAPI.getSyncLogs(configId);
      setLogs(response.data);
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      if (error.response?.status === 404) {
        setError('Sync configuration not found. It may have been deleted.');
      } else {
        setError(error.response?.data?.detail || 'Failed to fetch sync history');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchLogs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, configId]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <SmallChip
            variant="status-success"
            icon={<CheckCircle sx={{ fontSize: 16 }} />}
            label="Success"
          />
        );
      case 'failed':
        return (
          <SmallChip
            variant="status-error"
            icon={<ErrorIcon sx={{ fontSize: 16 }} />}
            label="Failed"
          />
        );
      case 'running':
        return (
          <SmallChip
            variant="status-running"
            label="Running"
          />
        );
      default:
        return (
          <SmallChip
            variant="status-inactive"
            label={status}
          />
        );
    }
  };

  return (
    <StyledDialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
    >
      <DialogTitle sx={{ pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <History sx={{ fontSize: 24, color: APP_COLORS.text.secondary }} />
            <TypographyLabel
              sx={{
                fontSize: '20px',
                fontWeight: 400,
                letterSpacing: '-0.2px',
              }}
            >
              Sync history
            </TypographyLabel>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <StyledIconButton
              onClick={fetchLogs}
              size="small"
            >
              <Refresh fontSize="small" />
            </StyledIconButton>
            <StyledIconButton
              onClick={onClose}
              size="small"
            >
              <Close fontSize="small" />
            </StyledIconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: 3, pb: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
            <CircularProgress size={32} sx={{ color: APP_COLORS.brand.primary }} />
          </Box>
        ) : error ? (
          <Box
            sx={{
              py: 6,
              textAlign: 'center',
              bgcolor: APP_COLORS.status.errorBg,
              borderRadius: 2,
            }}
          >
            <TypographyLabel variant="label" sx={{ color: APP_COLORS.status.error }}>{error}</TypographyLabel>
          </Box>
        ) : logs.length === 0 ? (
          <Box
            sx={{
              py: 6,
              textAlign: 'center',
              bgcolor: APP_COLORS.surface.background,
              borderRadius: 2,
            }}
          >
            <TypographyLabel variant="label">
              No sync history available
            </TypographyLabel>
          </Box>
        ) : (
          <TableContainer
            sx={{
              border: `1px solid ${APP_COLORS.surface.border}`,
              borderRadius: 2,
              bgcolor: 'white',
            }}
          >
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: APP_COLORS.surface.background }}>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: `1px solid ${APP_COLORS.surface.border}`,
                    }}
                  >
                    Started At
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: `1px solid ${APP_COLORS.surface.border}`,
                    }}
                  >
                    Completed At
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: `1px solid ${APP_COLORS.surface.border}`,
                    }}
                  >
                    Status
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Events Created
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Events Updated
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Events Deleted
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: APP_COLORS.text.secondary,
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Error
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow
                    key={log.id}
                    sx={{
                      '&:hover': {
                        bgcolor: APP_COLORS.surface.background,
                      },
                      '&:last-child td': {
                        borderBottom: 0,
                      },
                    }}
                  >
                    <TableCell
                      sx={{
                        fontSize: '13px',
                        color: APP_COLORS.text.primary,
                        borderBottom: '1px solid #f1f3f4',
                      }}
                    >
                      {formatDate(log.started_at)}
                    </TableCell>
                    <TableCell
                      sx={{
                        fontSize: '13px',
                        color: APP_COLORS.text.primary,
                        borderBottom: '1px solid #f1f3f4',
                      }}
                    >
                      {log.completed_at ? formatDate(log.completed_at) : (
                        <TypographyLabel variant="caption">-</TypographyLabel>
                      )}
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      {getStatusChip(log.status)}
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <SmallChip
                        variant="outlined"
                        label={log.events_created}
                        sx={{ color: APP_COLORS.status.success }}
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <SmallChip
                        variant="outlined"
                        label={log.events_updated}
                        sx={{ color: APP_COLORS.brand.secondary }}
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <SmallChip
                        variant="outlined"
                        label={log.events_deleted}
                        sx={{ color: APP_COLORS.status.warning }}
                      />
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      {log.error_message ? (
                        <TypographyLabel
                          variant="caption"
                          sx={{
                            color: APP_COLORS.status.error,
                          }}
                        >
                          {log.error_message}
                        </TypographyLabel>
                      ) : (
                        <TypographyLabel variant="caption">-</TypographyLabel>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3, pt: 0 }}>
        <SecondaryButton onClick={onClose}>
          Close
        </SecondaryButton>
      </DialogActions>
    </StyledDialog>
  );
}
