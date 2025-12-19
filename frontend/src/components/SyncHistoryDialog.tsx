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
  Paper,
  Chip,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, History } from '@mui/icons-material';
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

  useEffect(() => {
    if (open) {
      fetchLogs();
    }
  }, [open, configId]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await syncAPI.getSyncLogs(configId);
      setLogs(response.data);
    } catch (err: any) {
      setError('Failed to fetch sync history');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'success':
        return <Chip icon={<CheckCircle />} label="Success" color="success" size="small" />;
      case 'failed':
        return <Chip icon={<ErrorIcon />} label="Failed" color="error" size="small" />;
      case 'running':
        return <Chip label="Running" color="info" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <History />
          Sync History
        </Box>
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : logs.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
            No sync history available
          </Typography>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Started At</TableCell>
                  <TableCell>Completed At</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Created</TableCell>
                  <TableCell align="right">Updated</TableCell>
                  <TableCell align="right">Deleted</TableCell>
                  <TableCell>Error</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{formatDate(log.started_at)}</TableCell>
                    <TableCell>
                      {log.completed_at ? formatDate(log.completed_at) : '-'}
                    </TableCell>
                    <TableCell>{getStatusChip(log.status)}</TableCell>
                    <TableCell align="right">
                      <Chip label={log.events_created} color="success" size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <Chip label={log.events_updated} color="info" size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <Chip label={log.events_deleted} color="warning" size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {log.error_message ? (
                        <Typography variant="caption" color="error">
                          {log.error_message}
                        </Typography>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button onClick={fetchLogs} variant="outlined">
          Refresh
        </Button>
      </DialogActions>
    </Dialog>
  );
}
