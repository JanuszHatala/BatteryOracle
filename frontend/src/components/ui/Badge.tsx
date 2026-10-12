import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'optimal' | 'elevated' | 'severe' | 'neutral' | 'scope' | 'info';
}

export const Badge: React.FC<BadgeProps> = ({ children, className, variant = 'neutral', ...props }) => {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold select-none';

  const variants = {
    optimal: 'bg-emerald-950 text-emerald-400 border border-emerald-800/60',
    elevated: 'bg-amber-950 text-amber-400 border border-amber-800/60',
    severe: 'bg-rose-950 text-rose-400 border border-rose-800/60',
    neutral: 'bg-slate-800 text-slate-300 border border-slate-700',
    scope: 'bg-indigo-950/80 text-indigo-300 border border-indigo-700/60',
    info: 'bg-sky-950 text-sky-400 border border-sky-800/60'
  };

  return (
    <span className={twMerge(clsx(baseStyles, variants[variant], className))} {...props}>
      {children}
    </span>
  );
};
