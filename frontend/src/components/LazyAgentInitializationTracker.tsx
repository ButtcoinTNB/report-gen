import dynamic from 'next/dynamic';

// Import the component dynamically with SSR disabled
// This prevents browser-specific code from running during server-side rendering
const LazyAgentInitializationTracker = dynamic(
  () => import('./AgentInitializationTracker'), 
  { 
    ssr: false,
    loading: () => <div className="agent-tracker-loading">Loading tracker...</div>
  }
);

export default LazyAgentInitializationTracker; 