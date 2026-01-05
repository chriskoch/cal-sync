import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Alert,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Card,
  Link,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import { PlayArrow, Circle, Lock, Close, Add, ArrowForward, SyncAlt, Check } from '@mui/icons-material';
import CalendarSelector from './CalendarSelector';
import { syncAPI, SyncConfig } from '../services/api';
import { CALENDAR_COLORS } from '../constants/colors';

interface SyncConfigFormProps {
  onConfigCreated?: (config: SyncConfig) => void;
}

export default function SyncConfigForm({ onConfigCreated }: SyncConfigFormProps) {
  const [open, setOpen] = useState(false);
  const [sourceCalendarId, setSourceCalendarId] = useState('');
  const [sourceCalendarName, setSourceCalendarName] = useState('');
  const [destCalendarId, setDestCalendarId] = useState('');
  const [destCalendarName, setDestCalendarName] = useState('');
  const [syncLookaheadDays, setSyncLookaheadDays] = useState(90);
  const [destinationColorId, setDestinationColorId] = useState('');
  const [reverseDestinationColorId, setReverseDestinationColorId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Bi-directional sync settings
  const [enableBidirectional, setEnableBidirectional] = useState(false);

  // Privacy mode settings (Business→Private direction)
  const [privacyModeEnabled, setPrivacyModeEnabled] = useState(false);
  const [privacyPlaceholderText, setPrivacyPlaceholderText] = useState('Personal appointment');

  // Privacy mode settings (Private→Business direction)
  const [reversePrivacyModeEnabled, setReversePrivacyModeEnabled] = useState(false);
  const [reversePrivacyPlaceholderText, setReversePrivacyPlaceholderText] = useState('Personal appointment');

  // Auto-sync scheduling
  const [autoSyncEnabled, setAutoSyncEnabled] = useState(false);
  const [cronExpression, setCronExpression] = useState('0 */6 * * *'); // Default: every 6 hours
  const [timezone, setTimezone] = useState('UTC');

  const handleOpen = () => {
    setOpen(true);
    // Reset form
    setSourceCalendarId('');
    setSourceCalendarName('');
    setDestCalendarId('');
    setDestCalendarName('');
    setSyncLookaheadDays(90);
    setDestinationColorId('');
    setReverseDestinationColorId('');
    setEnableBidirectional(false);
    setPrivacyModeEnabled(false);
    setPrivacyPlaceholderText('Personal appointment');
    setReversePrivacyModeEnabled(false);
    setReversePrivacyPlaceholderText('Personal appointment');
    setAutoSyncEnabled(false);
    setCronExpression('0 */6 * * *');
    setTimezone('UTC');
    setError('');
    setSuccess('');
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!sourceCalendarId || !destCalendarId) {
      setError('Please select both Business and Private calendars');
      return;
    }

    if (sourceCalendarId === destCalendarId) {
      setError('Business and Private calendars must be different');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const response = await syncAPI.createConfig({
        source_calendar_id: sourceCalendarId,
        dest_calendar_id: destCalendarId,
        sync_lookahead_days: syncLookaheadDays,
        destination_color_id: destinationColorId || undefined,
        enable_bidirectional: enableBidirectional,
        privacy_mode_enabled: privacyModeEnabled,
        privacy_placeholder_text: privacyModeEnabled ? privacyPlaceholderText : undefined,
        reverse_privacy_mode_enabled: enableBidirectional ? reversePrivacyModeEnabled : undefined,
        reverse_privacy_placeholder_text:
          enableBidirectional && reversePrivacyModeEnabled ? reversePrivacyPlaceholderText : undefined,
        reverse_destination_color_id: enableBidirectional && reverseDestinationColorId ? reverseDestinationColorId : undefined,
        auto_sync_enabled: autoSyncEnabled,
        auto_sync_cron: autoSyncEnabled ? cronExpression : undefined,
        auto_sync_timezone: autoSyncEnabled ? timezone : 'UTC',
      });

      setSuccess(
        enableBidirectional
          ? 'Bi-directional sync created successfully!'
          : 'Sync created successfully!'
      );

      if (onConfigCreated) {
        onConfigCreated(response.data);
      }

      // Close modal after short delay to show success message
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to create sync configuration');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Trigger Button */}
      <Button
        variant="contained"
        startIcon={<Add />}
        onClick={handleOpen}
        sx={{
          textTransform: 'none',
          fontSize: '14px',
          fontWeight: 500,
          borderRadius: 2,
          px: 3,
          bgcolor: '#1a73e8',
          '&:hover': {
            bgcolor: '#1765cc',
          },
        }}
      >
        Create new sync
      </Button>

      {/* Modal Dialog */}
      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="md"
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
            <Typography
              variant="h6"
              sx={{
                fontSize: '20px',
                fontWeight: 400,
                color: '#202124',
                letterSpacing: '-0.2px',
              }}
            >
              Create new sync
            </Typography>
            <IconButton
              onClick={handleClose}
              size="small"
              sx={{
                color: '#5f6368',
                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
              }}
            >
              <Close fontSize="small" />
            </IconButton>
          </Box>
          <Typography
            variant="body2"
            sx={{
              fontSize: '14px',
              color: '#5f6368',
              mt: 0.5,
            }}
          >
            Select calendars from your connected accounts. Events will sync between them.
          </Typography>
        </DialogTitle>

        <DialogContent sx={{ px: 3, pb: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 3, borderRadius: 2 }}>
              {success}
            </Alert>
          )}

          <form onSubmit={handleSubmit} id="sync-config-form">
            <Grid container spacing={3}>
              {/* Sync Type Selection */}
              <Grid item xs={12}>
                <ToggleButtonGroup
                  value={enableBidirectional ? 'bidirectional' : 'oneway'}
                  exclusive
                  onChange={(_, newValue) => {
                    if (newValue !== null) {
                      setEnableBidirectional(newValue === 'bidirectional');
                    }
                  }}
                  fullWidth
                  sx={{
                    '& .MuiToggleButton-root': {
                      textTransform: 'none',
                      py: 1.5,
                      px: 2,
                      border: '1px solid #dadce0',
                      color: '#5f6368',
                      bgcolor: 'white',
                      '&:hover': {
                        bgcolor: '#f8f9fa',
                      },
                      '&.Mui-selected': {
                        bgcolor: '#1a73e8',
                        color: 'white',
                        border: '1px solid #1a73e8',
                        '&:hover': {
                          bgcolor: '#1765cc',
                        },
                      },
                    },
                  }}
                >
                  <ToggleButton value="oneway">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <ArrowForward sx={{ fontSize: 20 }} />
                      <Typography sx={{ fontSize: '14px', fontWeight: 500 }}>
                        One-way sync
                      </Typography>
                    </Box>
                  </ToggleButton>
                  <ToggleButton value="bidirectional">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SyncAlt sx={{ fontSize: 20 }} />
                      <Typography sx={{ fontSize: '14px', fontWeight: 500 }}>
                        Bi-directional sync
                      </Typography>
                    </Box>
                  </ToggleButton>
                </ToggleButtonGroup>

                <Typography
                  variant="body2"
                  sx={{
                    mt: 1,
                    fontSize: '13px',
                    color: '#5f6368',
                  }}
                >
                  {enableBidirectional
                    ? 'Events will sync in both directions between the selected calendars'
                    : 'Events will sync from Account 1 to Account 2 only'}
                </Typography>
              </Grid>

              {/* Calendar Selectors */}
              <Grid item xs={12} md={6}>
                <CalendarSelector
                  accountType="source"
                  value={sourceCalendarId}
                  onChange={(id, calendar) => {
                    setSourceCalendarId(id);
                    setSourceCalendarName(calendar?.summary || '');

                    // Auto-select Business calendar's color for Private calendar
                    if (calendar?.color_id && calendar.color_id.trim() !== '') {
                      const isValidColorId = CALENDAR_COLORS.some(c => c.id === calendar.color_id);
                      if (isValidColorId) {
                        setDestinationColorId(calendar.color_id);
                      } else {
                        setDestinationColorId(CALENDAR_COLORS[0].id);
                      }
                    } else if (calendar?.background_color) {
                      const matchedColor = CALENDAR_COLORS.find(
                        c => c.color.toLowerCase() === calendar.background_color?.toLowerCase()
                      );
                      if (matchedColor) {
                        setDestinationColorId(matchedColor.id);
                      } else {
                        setDestinationColorId(CALENDAR_COLORS[0].id);
                      }
                    } else {
                      setDestinationColorId('');
                    }
                  }}
                  label="Calendar from Account 1"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <CalendarSelector
                  accountType="destination"
                  value={destCalendarId}
                  onChange={(id, calendar) => {
                    setDestCalendarId(id);
                    setDestCalendarName(calendar?.summary || '');
                  }}
                  label="Calendar from Account 2"
                />
              </Grid>

              {/* Sync Settings */}
              <Grid item xs={12} md={enableBidirectional ? 6 : 12}>
                <Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#202124',
                      mb: 1.5,
                    }}
                  >
                    {enableBidirectional
                      ? `Event color (${sourceCalendarName || 'Account 1'} → ${destCalendarName || 'Account 2'})`
                      : 'Event color'}
                  </Typography>
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(32px, 1fr))',
                      gap: 1,
                      p: 2,
                      border: '1px solid #dadce0',
                      borderRadius: 2,
                      bgcolor: '#f8f9fa',
                    }}
                  >
                    {/* "Same as source" option */}
                    <Box
                      onClick={() => setDestinationColorId('')}
                      sx={{
                        width: 32,
                        height: 32,
                        borderRadius: 1,
                        border: '1px solid #dadce0',
                        bgcolor: 'white',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                        transition: 'all 0.2s',
                        '&:hover': {
                          transform: 'scale(1.15)',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                        },
                      }}
                      title="Same as source"
                    >
                      {destinationColorId === '' ? (
                        <Check sx={{ fontSize: 18, color: '#1a73e8', fontWeight: 'bold' }} />
                      ) : (
                        <Box sx={{ fontSize: '16px', color: '#5f6368', lineHeight: 1 }}>≈</Box>
                      )}
                    </Box>
                    {CALENDAR_COLORS.map((colorOption) => (
                      <Box
                        key={colorOption.id}
                        onClick={() => setDestinationColorId(colorOption.id)}
                        sx={{
                          width: 32,
                          height: 32,
                          borderRadius: 1,
                          border: '1px solid #dadce0',
                          bgcolor: colorOption.color,
                          cursor: 'pointer',
                          position: 'relative',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.2s',
                          '&:hover': {
                            transform: 'scale(1.15)',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                          },
                        }}
                        title={colorOption.name}
                      >
                        {destinationColorId === colorOption.id && (
                          <Check
                            sx={{
                              fontSize: 20,
                              color: 'white',
                              filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.4))',
                              fontWeight: 'bold',
                            }}
                          />
                        )}
                      </Box>
                    ))}
                  </Box>
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      mt: 1,
                      ml: 0.5,
                      fontSize: '12px',
                      color: '#5f6368',
                    }}
                  >
                    {destinationColorId === ''
                      ? 'Same as source calendar'
                      : CALENDAR_COLORS.find(c => c.id === destinationColorId)?.name || 'Select a color'}
                  </Typography>
                </Box>
              </Grid>

              {/* Reverse direction color picker (only for bi-directional) */}
              {enableBidirectional && (
                <Grid item xs={12} md={6}>
                  <Box>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '13px',
                        fontWeight: 500,
                        color: '#202124',
                        mb: 1.5,
                      }}
                    >
                      Event color ({destCalendarName || 'Account 2'} → {sourceCalendarName || 'Account 1'})
                    </Typography>
                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(32px, 1fr))',
                        gap: 1,
                        p: 2,
                        border: '1px solid #dadce0',
                        borderRadius: 2,
                        bgcolor: '#f8f9fa',
                      }}
                    >
                      {/* "Same as source" option */}
                      <Box
                        onClick={() => setReverseDestinationColorId('')}
                        sx={{
                          width: 32,
                          height: 32,
                          borderRadius: 1,
                          border: '1px solid #dadce0',
                          bgcolor: 'white',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          position: 'relative',
                          transition: 'all 0.2s',
                          '&:hover': {
                            transform: 'scale(1.15)',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                          },
                        }}
                        title="Same as source"
                      >
                        {reverseDestinationColorId === '' ? (
                          <Check sx={{ fontSize: 18, color: '#1a73e8', fontWeight: 'bold' }} />
                        ) : (
                          <Box sx={{ fontSize: '16px', color: '#5f6368', lineHeight: 1 }}>≈</Box>
                        )}
                      </Box>
                      {CALENDAR_COLORS.map((colorOption) => (
                        <Box
                          key={colorOption.id}
                          onClick={() => setReverseDestinationColorId(colorOption.id)}
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: 1,
                            border: '1px solid #dadce0',
                            bgcolor: colorOption.color,
                            cursor: 'pointer',
                            position: 'relative',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s',
                            '&:hover': {
                              transform: 'scale(1.15)',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                            },
                          }}
                          title={colorOption.name}
                        >
                          {reverseDestinationColorId === colorOption.id && (
                            <Check
                              sx={{
                                fontSize: 20,
                                color: 'white',
                                filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.4))',
                                fontWeight: 'bold',
                              }}
                            />
                          )}
                        </Box>
                      ))}
                    </Box>
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'block',
                        mt: 1,
                        ml: 0.5,
                        fontSize: '12px',
                        color: '#5f6368',
                      }}
                    >
                      {reverseDestinationColorId === ''
                        ? 'Same as source calendar'
                        : CALENDAR_COLORS.find(c => c.id === reverseDestinationColorId)?.name || 'Select a color'}
                    </Typography>
                  </Box>
                </Grid>
              )}

              <Grid item xs={12} md={enableBidirectional ? 12 : 6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Sync lookahead days"
                  value={syncLookaheadDays}
                  onChange={(e) => setSyncLookaheadDays(Number(e.target.value))}
                  helperText="How many days in the future to sync"
                  inputProps={{ min: 1, max: 365 }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': {
                        borderColor: '#dadce0',
                      },
                      '&:hover fieldset': {
                        borderColor: '#1967d2',
                      },
                    },
                  }}
                />
              </Grid>

              {/* Privacy Settings */}
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }}>
                  <Chip
                    icon={<Lock sx={{ fontSize: 16 }} />}
                    label="Privacy settings"
                    sx={{
                      fontSize: '13px',
                      height: 28,
                      bgcolor: '#f1f3f4',
                      color: '#5f6368',
                      border: 'none',
                    }}
                  />
                </Divider>
              </Grid>

              {/* Business→Private Privacy */}
              <Grid item xs={12} md={enableBidirectional ? 6 : 12}>
                <Card
                  elevation={0}
                  sx={{
                    border: '1px solid #dadce0',
                    borderRadius: 2,
                    bgcolor: '#f8f9fa',
                  }}
                >
                  <Box sx={{ p: 2.5 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{
                        fontSize: '14px',
                        fontWeight: 500,
                        color: '#202124',
                        mb: 1.5,
                      }}
                    >
                      {enableBidirectional
                        ? `${sourceCalendarName || 'Account 1'} → ${destCalendarName || 'Account 2'}`
                        : 'Privacy mode'}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '13px',
                        color: '#5f6368',
                        mb: 1.5,
                      }}
                    >
                      Share your availability without revealing event details
                    </Typography>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={privacyModeEnabled}
                          onChange={(e) => setPrivacyModeEnabled(e.target.checked)}
                          size="small"
                          sx={{
                            '& .MuiSwitch-switchBase.Mui-checked': {
                              color: '#1a73e8',
                            },
                            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                              backgroundColor: '#1a73e8',
                            },
                          }}
                        />
                      }
                      label={
                        <Typography sx={{ fontSize: '14px', color: '#202124' }}>
                          Hide event details
                        </Typography>
                      }
                    />

                    {privacyModeEnabled && (
                      <TextField
                        fullWidth
                        label="Placeholder text"
                        value={privacyPlaceholderText}
                        onChange={(e) => setPrivacyPlaceholderText(e.target.value)}
                        helperText="Events will show this text instead of actual details"
                        size="small"
                        sx={{
                          mt: 2,
                          bgcolor: 'white',
                          '& .MuiOutlinedInput-root': {
                            '& fieldset': {
                              borderColor: '#dadce0',
                            },
                            '&:hover fieldset': {
                              borderColor: '#1967d2',
                            },
                          },
                        }}
                      />
                    )}

                    <Alert
                      severity="info"
                      sx={{
                        mt: 2,
                        bgcolor: 'white',
                        borderRadius: 2,
                        fontSize: '13px',
                        '& .MuiAlert-icon': {
                          fontSize: 18,
                        },
                      }}
                    >
                      Event titles, descriptions, and locations will be replaced with your placeholder text. Times remain visible for calendar blocking.
                    </Alert>
                  </Box>
                </Card>
              </Grid>

              {/* Private→Business Privacy */}
              {enableBidirectional && (
                <Grid item xs={12} md={6}>
                  <Card
                    elevation={0}
                    sx={{
                      border: '1px solid #dadce0',
                      borderRadius: 2,
                      bgcolor: '#f8f9fa',
                    }}
                  >
                    <Box sx={{ p: 2.5 }}>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontSize: '14px',
                          fontWeight: 500,
                          color: '#202124',
                          mb: 1.5,
                        }}
                      >
                        {destCalendarName || 'Account 2'} → {sourceCalendarName || 'Account 1'}
                      </Typography>

                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '13px',
                          color: '#5f6368',
                          mb: 1.5,
                        }}
                      >
                        Share your availability without revealing event details
                      </Typography>

                      <FormControlLabel
                        control={
                          <Switch
                            checked={reversePrivacyModeEnabled}
                            onChange={(e) => setReversePrivacyModeEnabled(e.target.checked)}
                            size="small"
                            sx={{
                              '& .MuiSwitch-switchBase.Mui-checked': {
                                color: '#1a73e8',
                              },
                              '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                                backgroundColor: '#1a73e8',
                              },
                            }}
                          />
                        }
                        label={
                          <Typography sx={{ fontSize: '14px', color: '#202124' }}>
                            Hide event details
                          </Typography>
                        }
                      />

                      {reversePrivacyModeEnabled && (
                        <TextField
                          fullWidth
                          label="Placeholder text"
                          value={reversePrivacyPlaceholderText}
                          onChange={(e) => setReversePrivacyPlaceholderText(e.target.value)}
                          helperText="Events will show this text instead of actual details"
                          size="small"
                          sx={{
                            mt: 2,
                            bgcolor: 'white',
                            '& .MuiOutlinedInput-root': {
                              '& fieldset': {
                                borderColor: '#dadce0',
                              },
                              '&:hover fieldset': {
                                borderColor: '#1967d2',
                              },
                            },
                          }}
                        />
                      )}
                    </Box>
                  </Card>
                </Grid>
              )}

              {/* Auto-sync Scheduling */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontSize: '15px',
                    fontWeight: 600,
                    color: '#202124',
                    mb: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  }}
                >
                  <Box
                    component="span"
                    sx={{
                      width: 4,
                      height: 20,
                      bgcolor: '#1a73e8',
                      borderRadius: 1,
                    }}
                  />
                  Automatic Syncing
                </Typography>

                <Card
                  elevation={0}
                  sx={{
                    border: '1px solid #dadce0',
                    borderRadius: 2,
                    bgcolor: '#f8f9fa',
                  }}
                >
                  <Box sx={{ p: 2.5 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '13px',
                        color: '#5f6368',
                        mb: 1.5,
                      }}
                    >
                      Schedule automatic syncs using cron expressions
                    </Typography>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={autoSyncEnabled}
                          onChange={(e) => setAutoSyncEnabled(e.target.checked)}
                          size="small"
                          sx={{
                            '& .MuiSwitch-switchBase.Mui-checked': {
                              color: '#1a73e8',
                            },
                            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                              backgroundColor: '#1a73e8',
                            },
                          }}
                        />
                      }
                      label={
                        <Typography sx={{ fontSize: '14px', color: '#202124' }}>
                          Enable automatic syncing
                        </Typography>
                      }
                    />

                    {autoSyncEnabled && (
                      <>
                        <Box>
                          <TextField
                            fullWidth
                            label="Cron Schedule"
                            value={cronExpression}
                            onChange={(e) => setCronExpression(e.target.value)}
                            size="small"
                            sx={{
                              mt: 2,
                              bgcolor: 'white',
                              '& .MuiOutlinedInput-root': {
                                '& fieldset': {
                                  borderColor: '#dadce0',
                                },
                                '&:hover fieldset': {
                                  borderColor: '#1967d2',
                                },
                              },
                            }}
                          />
                          <Typography
                            variant="caption"
                            sx={{
                              display: 'block',
                              mt: 0.5,
                              ml: 1.75,
                              color: '#5f6368',
                              fontSize: '12px',
                            }}
                          >
                            e.g., '0 */6 * * *' for every 6 hours, '0 0 * * *' for daily at midnight.{' '}
                            <Link
                              href="https://crontab.cronhub.io/"
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={{
                                color: '#1a73e8',
                                textDecoration: 'none',
                                '&:hover': {
                                  textDecoration: 'underline',
                                },
                              }}
                            >
                              Need help? Use cron expression builder
                            </Link>
                          </Typography>
                        </Box>

                        <FormControl
                          fullWidth
                          size="small"
                          sx={{
                            mt: 2,
                            bgcolor: 'white',
                            '& .MuiOutlinedInput-root': {
                              '& fieldset': {
                                borderColor: '#dadce0',
                              },
                              '&:hover fieldset': {
                                borderColor: '#1967d2',
                              },
                            },
                          }}
                        >
                          <InputLabel>Timezone</InputLabel>
                          <Select
                            value={timezone}
                            onChange={(e) => setTimezone(e.target.value)}
                            label="Timezone"
                          >
                            <MenuItem value="UTC">UTC</MenuItem>
                            <MenuItem value="America/New_York">America/New_York (EST/EDT)</MenuItem>
                            <MenuItem value="America/Chicago">America/Chicago (CST/CDT)</MenuItem>
                            <MenuItem value="America/Denver">America/Denver (MST/MDT)</MenuItem>
                            <MenuItem value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</MenuItem>
                            <MenuItem value="Europe/London">Europe/London (GMT/BST)</MenuItem>
                            <MenuItem value="Europe/Paris">Europe/Paris (CET/CEST)</MenuItem>
                            <MenuItem value="Asia/Tokyo">Asia/Tokyo (JST)</MenuItem>
                            <MenuItem value="Asia/Shanghai">Asia/Shanghai (CST)</MenuItem>
                            <MenuItem value="Australia/Sydney">Australia/Sydney (AEST/AEDT)</MenuItem>
                          </Select>
                        </FormControl>
                      </>
                    )}
                  </Box>
                </Card>
              </Grid>
            </Grid>
          </form>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3, pt: 2 }}>
          <Button
            onClick={handleClose}
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
            type="submit"
            form="sync-config-form"
            variant="contained"
            startIcon={<PlayArrow />}
            disabled={loading || !sourceCalendarId || !destCalendarId}
            sx={{
              textTransform: 'none',
              fontSize: '14px',
              fontWeight: 500,
              borderRadius: 2,
              px: 3,
              bgcolor: '#1a73e8',
              '&:hover': {
                bgcolor: '#1765cc',
              },
              '&:disabled': {
                bgcolor: '#dadce0',
                color: '#5f6368',
              },
            }}
          >
            {loading ? 'Creating...' : 'Create sync'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
