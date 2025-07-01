// react-energy-platform/src/utils/constants.js
/**
 * Frontend application-wide constants.
 */

// Environment variable for API base URL (ensure this is set in .env)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Chart Colors
// These were identified as likely frontend-specific from the backend constants.
export const SECTOR_COLORS_LIST = [ // Changed to a list for easier iteration in charts
    { bg: 'rgba(99, 102, 241, 0.7)', border: 'rgba(99, 102, 241, 1)' }, // Indigo-ish
    { bg: 'rgba(244, 63, 94, 0.7)', border: 'rgba(244, 63, 94, 1)' },  // Rose-ish
    { bg: 'rgba(59, 130, 246, 0.7)', border: 'rgba(59, 130, 246, 1)' }, // Blue-ish
    { bg: 'rgba(245, 158, 11, 0.7)', border: 'rgba(245, 158, 11, 1)' }, // Amber-ish
    { bg: 'rgba(139, 92, 246, 0.7)', border: 'rgba(139, 92, 246, 1)'}, // Violet-ish
    { bg: 'rgba(34, 197, 94, 0.7)', border: 'rgba(34, 197, 94, 1)' },  // Green-ish
    { bg: 'rgba(168, 85, 247, 0.7)', border: 'rgba(168, 85, 247, 1)'}, // Purple-ish
    { bg: 'rgba(239, 68, 68, 0.7)', border: 'rgba(239, 68, 68, 1)' }   // Red-ish
    // Add more if needed, or use a color generation function
];

export const MODEL_COLORS_MAP = { // Changed to a map for easier lookup by model name
    'MLR': 'rgba(99, 102, 241, 0.8)',
    'SLR': 'rgba(244, 63, 94, 0.8)',
    'TimeSeries': 'rgba(59, 130, 246, 0.8)',
    'WAM': 'rgba(245, 158, 11, 0.8)',
    'User Data': 'rgba(139, 92, 246, 0.8)',
    'DefaultForecast': 'rgba(22, 163, 74, 0.8)' // Example for a default or another model
};

// UI Interaction Constants
export const NOTIFICATION_TIMEOUT = 5000; // ms
export const DEBOUNCE_DELAY = 300; // ms for input debounce

// User Roles (Example - define based on your application's auth system)
export const USER_ROLES = {
  ADMIN: 'admin',
  EDITOR: 'editor',
  VIEWER: 'viewer',
};

// Notification Types (Example)
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  INFO: 'info',
  WARNING: 'warning',
};

// Common Date/Time Formats (using date-fns tokens)
export const DATE_FORMAT_LONG = "MMMM d, yyyy 'at' h:mm a"; // e.g., January 1, 2023 at 5:30 PM
export const DATE_FORMAT_SHORT = 'yyyy-MM-dd'; // e.g., 2023-01-01
export const TIME_FORMAT_SIMPLE = 'p'; // e.g., 5:30 PM (locale sensitive)

// Polling intervals (if used for job status etc.)
export const JOB_STATUS_POLL_INTERVAL = 5000; // ms

// Default values for forms or settings
export const DEFAULT_TARGET_YEAR_FRONTEND = new Date().getFullYear() + 10; // Example

console.log("Frontend constants initialized.");
