import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function CountdownTimer({ deadline, className }: { deadline: string; className?: string }) {
  const [remaining, setRemaining] = useState('');
  const [urgency, setUrgency] = useState<'normal' | 'warning' | 'critical'>('normal');

  useEffect(() => {
    const update = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) {
        setRemaining('BREACHED');
        setUrgency('critical');
        return;
      }
      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      setRemaining(`${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`);
      if (mins < 5) setUrgency('critical');
      else if (mins < 10) setUrgency('warning');
      else setUrgency('normal');
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  return (
    <span
      className={cn(
        'font-mono text-atlas-mono font-medium tabular-nums',
        urgency === 'normal' && 'text-muted-foreground',
        urgency === 'warning' && 'text-status-warning',
        urgency === 'critical' && 'text-status-critical',
        className,
      )}
    >
      {remaining}
    </span>
  );
}
