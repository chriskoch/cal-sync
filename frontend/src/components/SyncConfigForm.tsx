import { useState } from 'react';
import {
  Box,
  Typography,
  Alert,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
  DialogTitle,
  DialogContent,
  DialogActions,
  Link,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import { PlayArrow, Lock, Close, Add, ArrowForward, SyncAlt } from '@mui/icons-material';
import CalendarSelector from './CalendarSelector';
import ColorPicker from './ColorPicker';
import { syncAPI, SyncConfig } from '../services/api';
import { CALENDAR_COLORS, APP_COLORS } from '../constants/colors';
import {
  StyledDialog,
  StyledIconButton,
  PrimaryButton,
  SecondaryButton,
  StyledTextField,
  InfoCard,
  SmallChip,
  TypographyLabel,
} from './common';

interface SyncConfigFormProps {
  onConfigCreated?: (config: SyncConfig) => void;
}

const styles = {
  toggleButton: {
    textTransform: 'none',
    py: 1.5,
    px: 2,
    border: `1px solid ${APP_COLORS.surface.border}`,
    color: APP_COLORS.text.secondary,
    bgcolor: 'white',
    '&:hover': {
      bgcolor: APP_COLORS.surface.background,
    },
    '&.Mui-selected': {
      bgcolor: APP_COLORS.brand.primary,
      color: 'white',
      border: `1px solid ${APP_COLORS.brand.primary}`,
      '&:hover': {
        bgcolor: APP_COLORS.brand.secondary,
      },
    },
  },
  helperText: {
    mt: 1,
    fontSize: '13px',
    color: APP_COLORS.text.secondary,
  },
  sectionHeader: {
    fontSize: '15px',
    fontWeight: 600,
    color: APP_COLORS.text.primary,
    mb: 2,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  headerAccent: {
    width: 4,
    height: 20,
    bgcolor: APP_COLORS.brand.primary,
    borderRadius: 1,
  },
  privacyCardTitle: {
    fontSize: '14px',
    fontWeight: 500,
    color: APP_COLORS.text.primary,
    mb: 1.5,
  },
  privacyCardDescription: {
    fontSize: '13px',
    color: APP_COLORS.text.secondary,
    mb: 1.5,
  },
  switchLabel: {
    fontSize: '14px',
    color: APP_COLORS.text.primary,
  },
  captionText: {
    display: 'block',
    mt: 0.5,
    ml: 1.75,
    color: APP_COLORS.text.secondary,
    fontSize: '12px',
  },
  link: {
    color: APP_COLORS.brand.primary,
    textDecoration: 'none',
    '&:hover': {
      textDecoration: 'underline',
    },
  },
} as const;

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
      <PrimaryButton
        startIcon={<Add />}
        onClick={handleOpen}
        sx={{ px: 3 }}
      >
        Create new sync
      </PrimaryButton>

      {/* Modal Dialog */}
      <StyledDialog
        open={open}
        onClose={handleClose}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ pb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <TypographyLabel
              variant="heading"
              sx={{
                fontSize: '20px',
                fontWeight: 400,
                letterSpacing: '-0.2px',
              }}
            >
              Create new sync
            </TypographyLabel>
            <StyledIconButton
              onClick={handleClose}
              size="small"
            >
              <Close fontSize="small" />
            </StyledIconButton>
          </Box>
          <TypographyLabel
            variant="label"
            sx={{
              fontSize: '14px',
              mt: 0.5,
            }}
          >
            Select calendars from your connected accounts. Events will sync between them.
          </TypographyLabel>
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
                    '& .MuiToggleButton-root': styles.toggleButton,
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

                <TypographyLabel
                  variant="caption"
                  sx={styles.helperText}
                >
                  {enableBidirectional
                    ? 'Events will sync in both directions between the selected calendars'
                    : 'Events will sync from Account 1 to Account 2 only'}
                </TypographyLabel>
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
                <ColorPicker
                  value={destinationColorId}
                  onChange={setDestinationColorId}
                  label={
                    enableBidirectional
                      ? `Event color (${sourceCalendarName || 'Account 1'} → ${destCalendarName || 'Account 2'})`
                      : 'Event color'
                  }
                />
              </Grid>

              {/* Reverse direction color picker (only for bi-directional) */}
              {enableBidirectional && (
                <Grid item xs={12} md={6}>
                  <ColorPicker
                    value={reverseDestinationColorId}
                    onChange={setReverseDestinationColorId}
                    label={`Event color (${destCalendarName || 'Account 2'} → ${sourceCalendarName || 'Account 1'})`}
                  />
                </Grid>
              )}

              <Grid item xs={12} md={enableBidirectional ? 12 : 6}>
                <StyledTextField
                  fullWidth
                  type="number"
                  label="Sync lookahead days"
                  value={syncLookaheadDays}
                  onChange={(e) => setSyncLookaheadDays(Number(e.target.value))}
                  helperText="How many days in the future to sync"
                  inputProps={{ min: 1, max: 365 }}
                />
              </Grid>

              {/* Privacy Settings */}
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }}>
                  <SmallChip
                    icon={<Lock sx={{ fontSize: 16 }} />}
                    label="Privacy settings"
                  />
                </Divider>
              </Grid>

              {/* Business→Private Privacy */}
              <Grid item xs={12} md={enableBidirectional ? 6 : 12}>
                <InfoCard variant="bordered">
                  <Box sx={{ p: 2.5 }}>
                    <TypographyLabel
                      variant="subheading"
                      sx={styles.privacyCardTitle}
                    >
                      {enableBidirectional
                        ? `${sourceCalendarName || 'Account 1'} → ${destCalendarName || 'Account 2'}`
                        : 'Privacy mode'}
                    </TypographyLabel>

                    <TypographyLabel
                      variant="caption"
                      sx={styles.privacyCardDescription}
                    >
                      Share your availability without revealing event details
                    </TypographyLabel>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={privacyModeEnabled}
                          onChange={(e) => setPrivacyModeEnabled(e.target.checked)}
                          size="small"
                          sx={{
                            '& .MuiSwitch-switchBase.Mui-checked': {
                              color: APP_COLORS.brand.primary,
                            },
                            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                              backgroundColor: APP_COLORS.brand.primary,
                            },
                          }}
                        />
                      }
                      label={
                        <TypographyLabel variant="body" sx={styles.switchLabel}>
                          Hide event details
                        </TypographyLabel>
                      }
                    />

                    {privacyModeEnabled && (
                      <StyledTextField
                        fullWidth
                        label="Placeholder text"
                        value={privacyPlaceholderText}
                        onChange={(e) => setPrivacyPlaceholderText(e.target.value)}
                        helperText="Events will show this text instead of actual details"
                        size="small"
                        sx={{
                          mt: 2,
                          bgcolor: 'white',
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
                </InfoCard>
              </Grid>

              {/* Private→Business Privacy */}
              {enableBidirectional && (
                <Grid item xs={12} md={6}>
                  <InfoCard variant="bordered">
                    <Box sx={{ p: 2.5 }}>
                      <TypographyLabel
                        variant="subheading"
                        sx={styles.privacyCardTitle}
                      >
                        {destCalendarName || 'Account 2'} → {sourceCalendarName || 'Account 1'}
                      </TypographyLabel>

                      <TypographyLabel
                        variant="caption"
                        sx={styles.privacyCardDescription}
                      >
                        Share your availability without revealing event details
                      </TypographyLabel>

                      <FormControlLabel
                        control={
                          <Switch
                            checked={reversePrivacyModeEnabled}
                            onChange={(e) => setReversePrivacyModeEnabled(e.target.checked)}
                            size="small"
                            sx={{
                              '& .MuiSwitch-switchBase.Mui-checked': {
                                color: APP_COLORS.brand.primary,
                              },
                              '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                                backgroundColor: APP_COLORS.brand.primary,
                              },
                            }}
                          />
                        }
                        label={
                          <TypographyLabel variant="body" sx={styles.switchLabel}>
                            Hide event details
                          </TypographyLabel>
                        }
                      />

                      {reversePrivacyModeEnabled && (
                        <StyledTextField
                          fullWidth
                          label="Placeholder text"
                          value={reversePrivacyPlaceholderText}
                          onChange={(e) => setReversePrivacyPlaceholderText(e.target.value)}
                          helperText="Events will show this text instead of actual details"
                          size="small"
                          sx={{
                            mt: 2,
                            bgcolor: 'white',
                          }}
                        />
                      )}
                    </Box>
                  </InfoCard>
                </Grid>
              )}

              {/* Auto-sync Scheduling */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <TypographyLabel
                  variant="subheading"
                  sx={styles.sectionHeader}
                >
                  <Box component="span" sx={styles.headerAccent} />
                  Automatic Syncing
                </TypographyLabel>

                <InfoCard variant="bordered">
                  <Box sx={{ p: 2.5 }}>
                    <TypographyLabel
                      variant="caption"
                      sx={styles.privacyCardDescription}
                    >
                      Schedule automatic syncs using cron expressions
                    </TypographyLabel>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={autoSyncEnabled}
                          onChange={(e) => setAutoSyncEnabled(e.target.checked)}
                          size="small"
                          sx={{
                            '& .MuiSwitch-switchBase.Mui-checked': {
                              color: APP_COLORS.brand.primary,
                            },
                            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                              backgroundColor: APP_COLORS.brand.primary,
                            },
                          }}
                        />
                      }
                      label={
                        <TypographyLabel variant="body" sx={styles.switchLabel}>
                          Enable automatic syncing
                        </TypographyLabel>
                      }
                    />

                    {autoSyncEnabled && (
                      <>
                        <Box>
                          <StyledTextField
                            fullWidth
                            label="Cron Schedule"
                            value={cronExpression}
                            onChange={(e) => setCronExpression(e.target.value)}
                            size="small"
                            sx={{
                              mt: 2,
                              bgcolor: 'white',
                            }}
                          />
                          <Typography
                            variant="caption"
                            sx={styles.captionText}
                          >
                            e.g., '0 */6 * * *' for every 6 hours, '0 0 * * *' for daily at midnight.{' '}
                            <Link
                              href="https://crontab.cronhub.io/"
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={styles.link}
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
                                borderColor: APP_COLORS.surface.border,
                              },
                              '&:hover fieldset': {
                                borderColor: APP_COLORS.brand.secondary,
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
                </InfoCard>
              </Grid>
            </Grid>
          </form>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3, pt: 2 }}>
          <SecondaryButton onClick={handleClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton
            type="submit"
            form="sync-config-form"
            startIcon={<PlayArrow />}
            disabled={loading || !sourceCalendarId || !destCalendarId}
            sx={{ px: 3 }}
          >
            {loading ? 'Creating...' : 'Create sync'}
          </PrimaryButton>
        </DialogActions>
      </StyledDialog>
    </>
  );
}
