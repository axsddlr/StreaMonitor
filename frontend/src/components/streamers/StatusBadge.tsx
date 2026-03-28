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
      {/* Dot with optional pulsing glow ring for live status */}
      <span className="relative inline-flex shrink-0 h-2 w-2" aria-hidden="true">
        {config.pulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75 animate-glow-ring',
              config.dotClass
            )}
          />
        )}
        <span
          className={cn(
            'relative inline-flex rounded-full h-2 w-2',
            config.dotClass,
            config.pulse && 'animate-status-pulse'
          )}
        />
      </span>
      <span>{config.label}</span>
    </span>
  )
}
