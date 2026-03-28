import { useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { STATUS_CONFIG } from '@/lib/constants'

export interface FilterState {
  username: string
  site: string
  status: string
}

interface StreamerFiltersProps {
  filters: FilterState
  sites: Record<string, string>
  onFiltersChange: (filters: FilterState) => void
  className?: string
}

export function StreamerFilters({
  filters,
  sites,
  onFiltersChange,
  className,
}: StreamerFiltersProps) {
  const handleUsernameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onFiltersChange({ ...filters, username: e.target.value })
    },
    [filters, onFiltersChange]
  )

  const handleSiteChange = useCallback(
    (value: string) => {
      onFiltersChange({ ...filters, site: value === 'all' ? '' : value })
    },
    [filters, onFiltersChange]
  )

  const handleStatusChange = useCallback(
    (value: string) => {
      onFiltersChange({ ...filters, status: value === 'all' ? '' : value })
    },
    [filters, onFiltersChange]
  )

  const handleClear = useCallback(() => {
    onFiltersChange({ username: '', site: '', status: '' })
  }, [onFiltersChange])

  const hasActiveFilters = filters.username !== '' || filters.site !== '' || filters.status !== ''

  const statusEntries = Object.entries(STATUS_CONFIG).filter(
    ([code]) => !['410', '3'].includes(code)
  )

  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder="Filter username..."
          value={filters.username}
          onChange={handleUsernameChange}
          className="h-8 pl-8 text-xs w-44"
          aria-label="Filter by username"
        />
      </div>

      <Select value={filters.site || 'all'} onValueChange={handleSiteChange}>
        <SelectTrigger className="h-8 text-xs w-36" aria-label="Filter by site">
          <SelectValue placeholder="All sites" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All sites</SelectItem>
          {Object.entries(sites).map(([slug, name]) => (
            <SelectItem key={slug} value={slug}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={filters.status || 'all'} onValueChange={handleStatusChange}>
        <SelectTrigger className="h-8 text-xs w-36" aria-label="Filter by status">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {statusEntries.map(([code, config]) => (
            <SelectItem key={code} value={code}>
              {config.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
          aria-label="Clear all filters"
        >
          <X className="h-3.5 w-3.5 mr-1" />
          Clear
        </Button>
      )}
    </div>
  )
}
