import { cn } from '@/lib/utils';

interface AtlasLogoProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'light' | 'dark';
  className?: string;
}

export function AtlasLogo({ size = 'md', variant = 'light', className }: AtlasLogoProps) {
  const sizes = {
    sm: { icon: 'h-7 w-7', text: 'text-[13px]', sub: 'text-[8px]' },
    md: { icon: 'h-9 w-9', text: 'text-[15px]', sub: 'text-[9px]' },
    lg: { icon: 'h-12 w-12', text: 'text-[22px]', sub: 'text-[10px]' },
  };
  const s = sizes[size];
  const textColor = variant === 'light' ? 'text-primary-foreground' : 'text-foreground';
  const subColor = variant === 'light' ? 'text-primary-foreground/40' : 'text-muted-foreground';

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <div className={cn(s.icon, 'rounded-lg bg-accent flex items-center justify-center relative overflow-hidden')}>
        {/* Professional geometric network node logo */}
        <svg viewBox="0 0 100 100" className="h-[75%] w-[75%]" fill="none">
          {/* Hexagon base representing stability and network */}
          <path d="M50 5 L90 27.5 L90 72.5 L50 95 L10 72.5 L10 27.5 Z" fill="currentColor" className="text-accent-foreground" opacity="0.1" />

          {/* Intersecting paths representing AIOps flows */}
          <path d="M50 15 L80 32.5 V67.5 L50 85 L20 67.5 V32.5 Z" stroke="currentColor" className="text-accent-foreground" strokeWidth="6" strokeLinejoin="round" />

          {/* Inner data node representation */}
          <path d="M50 35 L65 44 V56 L50 65 L35 56 V44 Z" fill="currentColor" className="text-accent-foreground" opacity="0.8" />

          {/* Central AI core pulse */}
          <circle cx="50" cy="50" r="4" fill="currentColor" className="text-primary" />

          {/* Connections from core to nodes */}
          <line x1="50" y1="50" x2="50" y2="35" stroke="currentColor" className="text-primary" strokeWidth="2" />
          <line x1="50" y1="50" x2="65" y2="56" stroke="currentColor" className="text-primary" strokeWidth="2" />
          <line x1="50" y1="50" x2="35" y2="56" stroke="currentColor" className="text-primary" strokeWidth="2" />

          {/* Outer glowing nodes */}
          <circle cx="50" cy="15" r="4" fill="currentColor" className="text-accent-foreground" />
          <circle cx="80" cy="32.5" r="4" fill="currentColor" className="text-accent-foreground" />
          <circle cx="80" cy="67.5" r="4" fill="currentColor" className="text-accent-foreground" />
          <circle cx="50" cy="85" r="4" fill="currentColor" className="text-accent-foreground" />
          <circle cx="20" cy="67.5" r="4" fill="currentColor" className="text-accent-foreground" />
          <circle cx="20" cy="32.5" r="4" fill="currentColor" className="text-accent-foreground" />
        </svg>
      </div>
      <div>
        <h1 className={cn(s.text, 'font-bold tracking-[0.15em] leading-none', textColor)}>ATLAS</h1>
        <p className={cn(s.sub, 'mt-0.5 tracking-[0.08em] uppercase', subColor)}>AIOps Platform</p>
      </div>
    </div>
  );
}
