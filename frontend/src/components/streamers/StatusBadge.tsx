import { cn } from '@/lib/utils'
import { getStatusConfig } from '@/lib/constants'

interface StatusBadgeProps {
  status_code: number
  status_text: string
  className?: string
}

export function StatusBadge({ status_code, status_text, className }: StatusBadgeProps) {
  const config = getStatusConfig(status_code)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-xs font-medium',
        config.colorClass,
        className
      )}
      title={`Status ${status_code}: ${status_text}`}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full shrink-0', config.dotClass)}
        aria-hidden="true"
      />
      <span>{config.label}</span>
    </span>
  )
}
