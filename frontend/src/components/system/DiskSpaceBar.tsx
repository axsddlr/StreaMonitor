import { cn } from '@/lib/utils'
import type { DiskSpaceDTO } from '@/lib/types'

interface DiskSpaceBarProps {
  disk: DiskSpaceDTO | null
  className?: string
}

function getBarColorClass(percentageFree: number): string {
  if (percentageFree > 30) return 'bg-emerald-500'
  if (percentageFree > 15) return 'bg-amber-400'
  return 'bg-red-500'
}

export function DiskSpaceBar({ disk, className }: DiskSpaceBarProps) {
  if (!disk) {
    return (
      <div className={cn('flex items-center gap-1.5 text-xs text-muted-foreground/60', className)}>
        <span className="tabular-nums">Disk: —</span>
      </div>
    )
  }

  const usedPercentage = 100 - disk.percentage_free
  const barColorClass = getBarColorClass(disk.percentage_free)
  const isCritical = disk.percentage_free <= 15

  return (
    <div className={cn('flex items-center gap-2 min-w-0', className)}>
      <span className={cn('text-xs whitespace-nowrap shrink-0 tabular-nums font-mono', isCritical ? 'text-red-400' : 'text-muted-foreground')}>
        {disk.free_human} free
      </span>
      <div
        className="h-1 w-20 shrink-0 rounded-full overflow-hidden"
        style={{ background: 'hsl(var(--secondary))' }}
        role="progressbar"
        aria-label={`Disk: ${usedPercentage.toFixed(0)}% used, ${disk.free_human} free of ${disk.total_human}`}
        aria-valuenow={usedPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn('h-full rounded-full transition-all duration-700', barColorClass)}
          style={{ width: `${usedPercentage}%` }}
        />
      </div>
      <span className={cn('text-xs whitespace-nowrap shrink-0 tabular-nums', isCritical ? 'text-red-400 font-medium' : 'text-muted-foreground/70')}>
        {disk.percentage_free.toFixed(0)}%
      </span>
    </div>
  )
}
