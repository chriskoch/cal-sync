import { Box, Typography } from '@mui/material';
import { Check } from '@mui/icons-material';
import { CALENDAR_COLORS } from '../constants/colors';

interface ColorPickerProps {
  value: string;
  onChange: (colorId: string) => void;
  label?: string;
}

const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(32px, 1fr))',
    gap: 1,
    p: 2,
    border: '1px solid #dadce0',
    borderRadius: 2,
    bgcolor: '#f8f9fa',
  },
  swatch: {
    width: 32,
    height: 32,
    borderRadius: 1,
    border: '1px solid #dadce0',
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
  },
  sameAsSourceSwatch: {
    bgcolor: 'white',
  },
  checkIcon: {
    fontSize: 20,
    color: 'white',
    filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.4))',
    fontWeight: 'bold',
  },
  blueCheckIcon: {
    fontSize: 18,
    color: '#1a73e8',
    fontWeight: 'bold',
  },
  symbolText: {
    fontSize: '16px',
    color: '#5f6368',
    lineHeight: 1,
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#202124',
    mb: 1.5,
  },
  caption: {
    display: 'block',
    mt: 1,
    ml: 0.5,
    fontSize: '12px',
    color: '#5f6368',
  },
} as const;

export default function ColorPicker({ value, onChange, label }: ColorPickerProps) {
  const selectedColorName = value === ''
    ? 'Same as source calendar'
    : CALENDAR_COLORS.find(c => c.id === value)?.name || 'Select a color';

  return (
    <Box>
      {label && (
        <Typography variant="body2" sx={styles.label}>
          {label}
        </Typography>
      )}

      <Box sx={styles.container}>
        {/* "Same as source" option */}
        <Box
          onClick={() => onChange('')}
          sx={{ ...styles.swatch, ...styles.sameAsSourceSwatch }}
          title="Same as source"
        >
          {value === '' ? (
            <Check sx={styles.blueCheckIcon} />
          ) : (
            <Box sx={styles.symbolText}>≈</Box>
          )}
        </Box>

        {/* Color swatches */}
        {CALENDAR_COLORS.map((colorOption) => (
          <Box
            key={colorOption.id}
            onClick={() => onChange(colorOption.id)}
            sx={{
              ...styles.swatch,
              bgcolor: colorOption.color,
            }}
            title={colorOption.name}
          >
            {value === colorOption.id && <Check sx={styles.checkIcon} />}
          </Box>
        ))}
      </Box>

      <Typography variant="caption" sx={styles.caption}>
        {selectedColorName}
      </Typography>
    </Box>
  );
}
