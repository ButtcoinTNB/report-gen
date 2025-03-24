import React from 'react';
import TaskDashboard from './TaskDashboard';

/**
 * Legacy Dashboard component that forwards to TaskDashboard
 * This is kept for backward compatibility
 */
const Dashboard: React.FC = () => {
  return <TaskDashboard />;
};

export default Dashboard; 