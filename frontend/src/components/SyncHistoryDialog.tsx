import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Typography,
  Box,
  CircularProgress,
  IconButton,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, History, Close, Refresh } from '@mui/icons-material';
import { syncAPI, SyncLog } from '../services/api';

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
          <Chip
            icon={<CheckCircle sx={{ fontSize: 16 }} />}
            label="Success"
            size="small"
            sx={{
              bgcolor: '#e6f4ea',
              color: '#1e8e3e',
              border: 'none',
              height: 24,
              fontSize: '12px',
            }}
          />
        );
      case 'failed':
        return (
          <Chip
            icon={<ErrorIcon sx={{ fontSize: 16 }} />}
            label="Failed"
            size="small"
            sx={{
              bgcolor: '#fce8e6',
              color: '#d93025',
              border: 'none',
              height: 24,
              fontSize: '12px',
            }}
          />
        );
      case 'running':
        return (
          <Chip
            label="Running"
            size="small"
            sx={{
              bgcolor: '#e8f0fe',
              color: '#1967d2',
              border: 'none',
              height: 24,
              fontSize: '12px',
            }}
          />
        );
      default:
        return (
          <Chip
            label={status}
            size="small"
            sx={{
              bgcolor: '#f1f3f4',
              color: '#5f6368',
              border: 'none',
              height: 24,
              fontSize: '12px',
            }}
          />
        );
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
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
            <History sx={{ fontSize: 24, color: '#5f6368' }} />
            <Typography
              variant="h6"
              sx={{
                fontSize: '20px',
                fontWeight: 400,
                color: '#202124',
                letterSpacing: '-0.2px',
              }}
            >
              Sync history
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton
              onClick={fetchLogs}
              size="small"
              sx={{
                color: '#5f6368',
                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
              }}
            >
              <Refresh fontSize="small" />
            </IconButton>
            <IconButton
              onClick={onClose}
              size="small"
              sx={{
                color: '#5f6368',
                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
              }}
            >
              <Close fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: 3, pb: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
            <CircularProgress size={32} sx={{ color: '#1a73e8' }} />
          </Box>
        ) : error ? (
          <Box
            sx={{
              py: 6,
              textAlign: 'center',
              bgcolor: '#fce8e6',
              borderRadius: 2,
            }}
          >
            <Typography sx={{ color: '#d93025', fontSize: '14px' }}>{error}</Typography>
          </Box>
        ) : logs.length === 0 ? (
          <Box
            sx={{
              py: 6,
              textAlign: 'center',
              bgcolor: '#f8f9fa',
              borderRadius: 2,
            }}
          >
            <Typography sx={{ color: '#5f6368', fontSize: '14px' }}>
              No sync history available
            </Typography>
          </Box>
        ) : (
          <TableContainer
            sx={{
              border: '1px solid #dadce0',
              borderRadius: 2,
              bgcolor: 'white',
            }}
          >
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#f8f9fa' }}>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#5f6368',
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Started At
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#5f6368',
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Completed At
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#5f6368',
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Status
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#5f6368',
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
                      color: '#5f6368',
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
                      color: '#5f6368',
                      borderBottom: '1px solid #dadce0',
                    }}
                  >
                    Events Deleted
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#5f6368',
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
                        bgcolor: '#f8f9fa',
                      },
                      '&:last-child td': {
                        borderBottom: 0,
                      },
                    }}
                  >
                    <TableCell
                      sx={{
                        fontSize: '13px',
                        color: '#202124',
                        borderBottom: '1px solid #f1f3f4',
                      }}
                    >
                      {formatDate(log.started_at)}
                    </TableCell>
                    <TableCell
                      sx={{
                        fontSize: '13px',
                        color: '#202124',
                        borderBottom: '1px solid #f1f3f4',
                      }}
                    >
                      {log.completed_at ? formatDate(log.completed_at) : (
                        <Typography sx={{ fontSize: '13px', color: '#5f6368' }}>-</Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      {getStatusChip(log.status)}
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <Chip
                        label={log.events_created}
                        size="small"
                        sx={{
                          bgcolor: 'transparent',
                          border: '1px solid #dadce0',
                          color: '#1e8e3e',
                          height: 24,
                          fontSize: '12px',
                        }}
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <Chip
                        label={log.events_updated}
                        size="small"
                        sx={{
                          bgcolor: 'transparent',
                          border: '1px solid #dadce0',
                          color: '#1967d2',
                          height: 24,
                          fontSize: '12px',
                        }}
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      <Chip
                        label={log.events_deleted}
                        size="small"
                        sx={{
                          bgcolor: 'transparent',
                          border: '1px solid #dadce0',
                          color: '#ea8600',
                          height: 24,
                          fontSize: '12px',
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #f1f3f4' }}>
                      {log.error_message ? (
                        <Typography
                          variant="caption"
                          sx={{
                            color: '#d93025',
                            fontSize: '12px',
                          }}
                        >
                          {log.error_message}
                        </Typography>
                      ) : (
                        <Typography sx={{ fontSize: '13px', color: '#5f6368' }}>-</Typography>
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
        <Button
          onClick={onClose}
          sx={{
            textTransform: 'none',
            fontSize: '14px',
            fontWeight: 500,
            borderRadius: 2,
            color: '#1967d2',
            '&:hover': {
              bgcolor: 'rgba(26, 115, 232, 0.04)',
            },
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
