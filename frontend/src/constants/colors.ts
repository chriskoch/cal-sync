/**
 * Google Calendar color palette constants
 *
 * Google Calendar supports 11 event colors (IDs 1-11) that can be set on individual events.
 * These are the only colors that can be assigned to synced events.
 */

export interface CalendarColor {
  id: string;
  name: string;
  color: string;
}

export const CALENDAR_COLORS: CalendarColor[] = [
  { id: '1', name: 'Lavender', color: '#7986cb' },
  { id: '2', name: 'Sage', color: '#33b679' },
  { id: '3', name: 'Grape', color: '#8e24aa' },
  { id: '4', name: 'Flamingo', color: '#e67c73' },
  { id: '5', name: 'Banana', color: '#f6c026' },
  { id: '6', name: 'Tangerine', color: '#f5511d' },
  { id: '7', name: 'Peacock', color: '#039be5' },
  { id: '8', name: 'Graphite', color: '#616161' },
  { id: '9', name: 'Blueberry', color: '#3f51b5' },
  { id: '10', name: 'Basil', color: '#0b8043' },
  { id: '11', name: 'Tomato', color: '#d60000' },
];

/**
 * Convert CALENDAR_COLORS array to object indexed by color ID
 * Useful for quick lookups by ID
 */
export const CALENDAR_COLORS_MAP: { [key: string]: { name: string; color: string } } =
  CALENDAR_COLORS.reduce((acc, color) => {
    acc[color.id] = { name: color.name, color: color.color };
    return acc;
  }, {} as { [key: string]: { name: string; color: string } });
