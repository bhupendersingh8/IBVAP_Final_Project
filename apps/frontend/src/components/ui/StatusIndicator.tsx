import React from 'react';

export type StatusType = 'online' | 'warning' | 'critical' | 'offline' | 'verified';

interface StatusIndicatorProps {
  status: StatusType;
  label?: string;
  className?: string;
  showDot?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  className = '',
  showDot = true,
}) => {
  const dotColors: Record<StatusType, string> = {
    online: 'bg-emerald-500',
    verified: 'bg-emerald-500',
    warning: 'bg-amber-500',
    critical: 'bg-red-500',
    offline: 'bg-slate-500',
  };

  const textColors: Record<StatusType, string> = {
    online: 'text-emerald-400',
    verified: 'text-emerald-400',
    warning: 'text-amber-400',
    critical: 'text-red-400',
    offline: 'text-slate-400',
  };

  const defaultLabels: Record<StatusType, string> = {
    online: 'Online',
    verified: 'Verified',
    warning: 'Warning',
    critical: 'Critical',
    offline: 'Offline',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${textColors[status]} ${className}`}>
      {showDot && (
        <span className={`w-2 h-2 rounded-full ${dotColors[status]}`} />
      )}
      {label ?? defaultLabels[status]}
    </span>
  );
};
