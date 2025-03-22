/**
 * Creates a throttled function that only invokes the provided function at most once per
 * every `wait` milliseconds.
 * 
 * @param func The function to throttle
 * @param wait The number of milliseconds to throttle invocations to
 * @returns A throttled version of the function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number = 250
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let lastArgs: Parameters<T> | null = null;
  let lastCallTime = 0;
  
  return function throttled(...args: Parameters<T>): void {
    const now = Date.now();
    lastArgs = args;
    
    if (!lastCallTime) {
      func(...args);
      lastCallTime = now;
      return;
    }
    
    const remaining = wait - (now - lastCallTime);
    
    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      func(...lastArgs);
      lastCallTime = now;
    } else if (!timeout) {
      timeout = setTimeout(() => {
        func(...(lastArgs as Parameters<T>));
        lastCallTime = Date.now();
        timeout = null;
        lastArgs = null;
      }, remaining);
    }
  };
}

/**
 * Creates a debounced function that delays invoking the provided function until after
 * `wait` milliseconds have elapsed since the last time it was invoked.
 * 
 * @param func The function to debounce
 * @param wait The number of milliseconds to delay
 * @returns A debounced version of the function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number = 250
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let lastArgs: Parameters<T> | null = null;
  
  return function debounced(...args: Parameters<T>): void {
    lastArgs = args;
    
    if (timeout) {
      clearTimeout(timeout);
    }
    
    timeout = setTimeout(() => {
      func(...(lastArgs as Parameters<T>));
      timeout = null;
      lastArgs = null;
    }, wait);
  };
} 