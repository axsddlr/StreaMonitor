import { cn } from '@/lib/utils'
import type { DiskSpaceDTO } from '@/lib/types'

interface DiskSpaceBarProps {
  disk: DiskSpaceDTO | null
  className?: string
}

function getBarColor(percentageFree: number): string {
  if (percentageFree > 30) return 'bg-green-500'
  if (percentageFree > 15) return 'bg-yellow-500'
  return 'bg-red-500'
}

export function DiskSpaceBar({ disk, className }: DiskSpaceBarProps) {
  if (!disk) {
    return (
      <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}>
        <span>Disk: loading...</span>
      </div>
    )
  }

  const usedPercentage = 100 - disk.percentage_free
  const barColor = getBarColor(disk.percentage_free)

  return (
    <div className={cn('flex items-center gap-2 min-w-0', className)}>
      <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
        Free: {disk.free_human} / {disk.total_human}
      </span>
      <div
        className="h-1.5 w-24 shrink-0 rounded-full bg-secondary overflow-hidden"
        role="progressbar"
        aria-label={`Disk usage: ${usedPercentage.toFixed(0)}% used`}
        aria-valuenow={usedPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${usedPercentage}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
        {disk.percentage_free.toFixed(1)}% free
      </span>
    </div>
  )
}
