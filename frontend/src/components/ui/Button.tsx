import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

type Variant = 'approve' | 'modify' | 'reject' | 'escalate' | 'ghost' | 'primary'

const variantMap: Record<Variant, string> = {
  approve:  'bg-emerald-600 hover:bg-emerald-700 text-white border border-emerald-500 shadow-sm',
  modify:   'bg-amber-500 hover:bg-amber-600 text-white border border-amber-400 shadow-sm',
  reject:   'bg-red-600 hover:bg-red-700 text-white border border-red-500 shadow-sm',
  escalate: 'bg-violet-600 hover:bg-violet-700 text-white border border-violet-500 shadow-sm',
  ghost:    'bg-white hover:bg-slate-50 text-subtle border border-border shadow-sm',
  primary:  'bg-blue-600 hover:bg-blue-700 text-white border border-blue-500 shadow-sm',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const sizeMap = {
  sm: 'px-3 py-1.5 text-xs rounded-lg',
  md: 'px-4 py-2 text-sm rounded-lg',
  lg: 'px-5 py-2.5 text-sm rounded-lg',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  children,
  className,
  ...props
}: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ scale: 1.01 }}
      transition={{ duration: 0.1 }}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-colors duration-150',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
        sizeMap[size],
        variantMap[variant],
        className,
      )}
      {...(props as React.ComponentProps<typeof motion.button>)}
    >
      {loading && (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {children}
    </motion.button>
  )
}
