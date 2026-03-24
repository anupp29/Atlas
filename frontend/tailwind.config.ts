import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ATLAS light design tokens
        canvas:   '#F0F4F8',
        surface:  '#FFFFFF',
        elevated: '#F8FAFC',
        border:   '#E2E8F0',
        muted:    '#94A3B8',
        // Status
        healthy:  '#059669',
        warning:  '#D97706',
        incident: '#DC2626',
        active:   '#2563EB',
        resolved: '#059669',
        veto:     '#DC2626',
        deploy:   '#B45309',
        history:  '#7C3AED',
        // Text
        ink:      '#0F172A',
        subtle:   '#475569',
        faint:    '#94A3B8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'card':    '0 1px 3px 0 rgba(0,0,0,0.08), 0 1px 2px -1px rgba(0,0,0,0.06)',
        'card-md': '0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)',
        'card-lg': '0 10px 15px -3px rgba(0,0,0,0.07), 0 4px 6px -4px rgba(0,0,0,0.05)',
        'glow-green': '0 0 0 3px rgba(5,150,105,0.15)',
        'glow-amber': '0 0 0 3px rgba(217,119,6,0.15)',
        'glow-red':   '0 0 0 3px rgba(220,38,38,0.15)',
        'glow-blue':  '0 0 0 3px rgba(37,99,235,0.15)',
      },
      animation: {
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow':  'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.35s ease-out',
        'shimmer':    'shimmer 1.5s infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
}

export default config
