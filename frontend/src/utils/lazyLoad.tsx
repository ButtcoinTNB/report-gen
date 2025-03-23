import dynamic from 'next/dynamic';
import React from 'react';

/**
 * Create a browser-only component (no SSR)
 * Use this for components that use browser-only APIs
 * 
 * @param importFunc Function that returns a dynamic import of a component
 * @returns Dynamically imported component with no SSR
 * 
 * @example
 * const Chart = browserComponent(() => import('../components/Chart'));
 */
export function browserComponent(importFunc: () => Promise<any>) {
  return dynamic(importFunc, {
    ssr: false,
  });
}

/**
 * Create a lazily-loaded component that still supports SSR
 * 
 * @param importFunc Function that returns a dynamic import of a component
 * @returns Dynamically imported component with SSR support
 * 
 * @example
 * const DataTable = lazyComponent(() => import('../components/DataTable'));
 */
export function lazyComponent(importFunc: () => Promise<any>) {
  return dynamic(importFunc);
}

/**
 * Create a lazily-loaded component with custom loading state
 * 
 * @param importFunc Function that returns a dynamic import of a component
 * @param LoadingComponent Component to show while loading
 * @returns Dynamically imported component with custom loading
 * 
 * @example
 * const DataTable = lazyComponentWithLoading(
 *   () => import('../components/DataTable'),
 *   () => <div>Loading...</div>
 * );
 */
export function lazyComponentWithLoading(
  importFunc: () => Promise<any>,
  LoadingComponent: React.ComponentType
) {
  return dynamic(importFunc, {
    loading: LoadingComponent,
  });
}

// Export a combined object for convenience
export default {
  browser: browserComponent,
  lazy: lazyComponent,
  withLoading: lazyComponentWithLoading,
}; 