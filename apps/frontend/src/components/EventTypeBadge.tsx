import React from 'react';

interface EventTypeBadgeProps {
  eventType: string;
  className?: string;
}

export const getEventTypeMeta = (eventType: string) => {
  const t = (eventType || '').toUpperCase();
  if (t.includes('DIRECTION_VIOLATION')) {
    return {
      label: 'DIRECTION VIOLATION',
      icon: '🧭',
      colorClass: 'bg-amber-100 text-amber-900 border-amber-300',
      description: 'Heading matched prohibited movement vector toward boundary',
    };
  }
  if (t.includes('LOITERING')) {
    return {
      label: 'LOITERING',
      icon: '⏳',
      colorClass: 'bg-purple-100 text-purple-900 border-purple-300',
      description: 'Sustained presence in restricted zone (dwell >= 15s)',
    };
  }
  if (t.includes('NIGHT_MOVEMENT')) {
    return {
      label: 'NIGHT MOVEMENT',
      icon: '🌙',
      colorClass: 'bg-indigo-100 text-indigo-900 border-indigo-300',
      description: 'Detected during border curfew hours (22:00-05:00 IST)',
    };
  }
  if (t.includes('REPEATED_ENTRY')) {
    return {
      label: 'REPEATED ENTRY',
      icon: '🔁',
      colorClass: 'bg-rose-100 text-rose-900 border-rose-300',
      description: 'Reconnaissance pattern: re-entered perimeter >= 3 times',
    };
  }
  if (t.includes('UNAUTHORIZED')) {
    return {
      label: 'UNAUTHORIZED PERSON',
      icon: '🛑',
      colorClass: 'bg-rose-600 text-white border-rose-700 font-bold',
      description: 'Unauthorized individual detected in camera surveillance view',
    };
  }
  if (t.includes('WEAPON') || t.includes('ARMED') || t.includes('GUN')) {
    return {
      label: 'ARMED WEAPON THREAT',
      icon: '🔫',
      colorClass: 'bg-red-700 text-white border-red-800 font-bold animate-pulse',
      description: 'Armed weapon (gun, knife, explosive) detected on live feed',
    };
  }
  if (t.includes('INTRUSION')) {
    return {
      label: 'ZONE INTRUSION',
      icon: '🚨',
      colorClass: 'bg-red-100 text-red-900 border-red-300',
      description: 'Physical perimeter breach into restricted sector',
    };
  }
  return {
    label: eventType.replace(/_/g, ' '),
    icon: '⚠️',
    colorClass: 'bg-slate-100 text-slate-800 border-slate-300',
    description: eventType,
  };
};

export const EventTypeBadge: React.FC<EventTypeBadgeProps> = ({ eventType, className = '' }) => {
  const meta = getEventTypeMeta(eventType);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border tracking-wide shadow-2xs ${meta.colorClass} ${className}`}
      title={meta.description}
    >
      <span className="text-xs">{meta.icon}</span>
      <span>{meta.label}</span>
    </span>
  );
};