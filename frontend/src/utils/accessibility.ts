/**
 * Utility functions for improving accessibility in our components
 */

/**
 * Create ARIA attributes for live announcements
 * @param region The type of live region
 * @returns ARIA attributes for the live region
 */
export function getLiveRegionProps(region: 'polite' | 'assertive' = 'polite') {
  return {
    'aria-live': region,
    'aria-atomic': true,
    role: 'status',
  };
}

/**
 * Create ARIA attributes for a loading indicator
 * @param isLoading Whether the element is loading
 * @param label Optional custom loading label
 * @returns ARIA attributes for loading state
 */
export function getLoadingProps(isLoading: boolean, label?: string) {
  if (!isLoading) return {};

  return {
    'aria-busy': 'true',
    'aria-label': label || 'Loading, please wait',
  };
}

/**
 * Create accessible props for a toggle button
 * @param isExpanded Whether the controlled element is expanded
 * @param controls ID of the element being controlled
 * @returns ARIA attributes for a toggle button
 */
export function getToggleButtonProps(isExpanded: boolean, controls: string) {
  return {
    'aria-expanded': isExpanded ? 'true' : 'false',
    'aria-controls': controls,
    role: 'button',
  };
}

/**
 * Create accessible props for a progressbar
 * @param value Current progress value (0-100)
 * @param label Optional label describing what's in progress
 * @returns ARIA attributes for a progress bar
 */
export function getProgressBarProps(value: number, label?: string) {
  return {
    role: 'progressbar',
    'aria-valuemin': 0,
    'aria-valuemax': 100,
    'aria-valuenow': Math.round(value),
    'aria-label': label || 'Progress',
  };
}

/**
 * Generate a unique ID for accessibility relationships
 * @param prefix Optional prefix for the ID
 * @returns A unique ID string
 */
export function generateAccessibleId(prefix: string = 'aria'): string {
  return `${prefix}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Create accessible error message props
 * @param errorId ID of the error message
 * @param hasError Whether there is an error
 * @returns ARIA attributes for form fields with errors
 */
export function getErrorProps(errorId: string, hasError: boolean) {
  if (!hasError) return {};
  
  return {
    'aria-invalid': 'true',
    'aria-errormessage': errorId,
  };
} 