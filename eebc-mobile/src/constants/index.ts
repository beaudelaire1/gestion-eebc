/**
 * Application constants
 */

export const API_BASE_URL = __DEV__
  ? 'http://localhost:8000/api/v1'
  : 'https://eglise-ebc.org/api/v1';

export const API_TIMEOUT = 30000; // 30 seconds

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
  MEMBERS_CACHE: 'members_cache',
  EVENTS_CACHE: 'events_cache',
  ANNOUNCEMENTS_CACHE: 'announcements_cache',
  OFFLINE_QUEUE: 'offline_queue',
  LAST_SYNC: 'last_sync',
  NOTIFICATION_PREFERENCES: 'notification_preferences',
  THEME_MODE: 'theme_mode',
  BIOMETRIC_ENABLED: 'biometric_enabled',
} as const;

export const CACHE_DURATION = {
  MEMBERS: 24 * 60 * 60 * 1000, // 24 hours
  EVENTS: 1 * 60 * 60 * 1000, // 1 hour
  ANNOUNCEMENTS: 30 * 60 * 1000, // 30 minutes
} as const;

export const MAX_LOGIN_ATTEMPTS = 5;
export const LOCKOUT_DURATION = 15 * 60 * 1000; // 15 minutes

export const NOTIFICATION_CHANNELS = {
  ANNOUNCEMENTS: 'announcements',
  EVENTS: 'events',
  WORSHIP: 'worship',
  DONATIONS: 'donations',
} as const;
