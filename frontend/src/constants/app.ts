export const PREVIEW = {
  MIN_ZOOM: 50,
  MAX_ZOOM: 200,
  ZOOM_STEP: 10,
  DEFAULT_HEIGHT: 500,
  FULLSCREEN_OFFSET: 200,
  DEFAULT_PAGE_SIZE: 10
} as const;

export const CACHE = {
  DOCUMENT_METADATA: 5 * 60, // 5 minutes in seconds
  PREVIEW_DATA: 30 * 60,    // 30 minutes in seconds
} as const;

export const TIMEOUTS = {
  STALL_THRESHOLD: 30 * 1000,     // 30 seconds
  TRANSACTION_CLEANUP: 5 * 60 * 1000,  // 5 minutes
  API_REQUEST: 30 * 1000,         // 30 seconds
  RETRY_DELAY: 2 * 1000,         // 2 seconds
} as const;

export const SHARE = {
  LINK_EXPIRATION: 86400, // 24 hours in seconds
  MAX_DOWNLOADS: 1, // Maximum number of downloads per share link
} as const;

export const ERROR_MESSAGES = {
  PREVIEW_LOAD: 'Failed to load document preview',
  NETWORK_ERROR: 'Network connection error',
  INVALID_FILE: 'Invalid file format or corrupted file',
  UNAUTHORIZED: 'You do not have permission to access this resource',
  SERVER_ERROR: 'Server error occurred',
  TIMEOUT: 'Request timed out',
} as const;

export const UI = {
  ANIMATION_DURATION: 200,
  DEBOUNCE_DELAY: 300,
  TOAST_DURATION: 5000,
} as const; 