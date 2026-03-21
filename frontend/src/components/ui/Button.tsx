import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

type Variant = 'approve' | 'modify' | 'reject' | 'escalate' | 'ghost' | 'primary'

const variantMap: Record<Variant, string> = {
  approve:  'bg-green-600 hover:bg-green-500 text-white border border-green-500 shadow-[0_0_12px_rgba(16,185,129,0.3)]',
  modify:   'bg-amber-600 hover:bg-amber-500 text-white border border-amber-500',
  reject:   'bg-red-700 hover:bg-red-600 text-white border border-red-600',
  escalate: 'bg-amber-700 hover:bg-amber-600 text-white border border-amber-600',
  ghost:    'bg-transparent hover:bg-elevated text-zinc-300 border border-border',
  primary:  'bg-blue-600 hover:bg-blue-500 text-white border border-blue-500',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const sizeMap = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
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
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors duration-150',
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
