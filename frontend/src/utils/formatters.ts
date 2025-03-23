/**
 * Utility functions for data formatting
 */

/**
 * Formats a number of bytes into a human-readable string
 * @param bytes Number of bytes to format
 * @param decimals Number of decimal places to include
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Formats a date into a localized string
 * @param date Date to format
 * @param options Intl.DateTimeFormatOptions
 * @returns Formatted date string
 */
export function formatDate(
  date: Date | string | number,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }
): string {
  const dateObj = date instanceof Date ? date : new Date(date);
  return new Intl.DateTimeFormat('it-IT', options).format(dateObj);
}

/**
 * Formats a number as a percentage
 * @param value Number to format as percentage
 * @param decimals Number of decimal places
 * @returns Formatted percentage string
 */
export function formatPercentage(value: number, decimals: number = 0): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Formats a number with thousand separators
 * @param num Number to format
 * @returns Formatted number string
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('it-IT').format(num);
}

/**
 * Formats a duration in seconds into a human-readable string
 * @param seconds Duration in seconds
 * @returns Formatted duration string (e.g., "2h 30m")
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) return `${hours}h`;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Truncates a string to a specified length and adds ellipsis if needed
 * @param str String to truncate
 * @param maxLength Maximum length before truncation
 * @returns Truncated string
 */
export function truncateString(str: string, maxLength: number = 50): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
}

export default {
  formatBytes,
  formatDate,
  formatPercentage,
  formatNumber,
  formatDuration,
  truncateString
}; 