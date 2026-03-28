import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { BulkActions } from '@/components/streamers/BulkActions'
import { AddStreamerDialog } from '@/components/streamers/AddStreamerDialog'
import { StreamerFilters, type FilterState } from '@/components/streamers/StreamerFilters'
import { StreamerTable } from '@/components/streamers/StreamerTable'
import { useWebSocket } from '@/hooks/useWebSocket'
import { getSettings } from '@/api/client'

interface DashboardProps {
  token: string | null
}

export function Dashboard({ token }: DashboardProps) {
  const [filters, setFilters] = useState<FilterState>({
    username: '',
    site: '',
    status: '',
  })

  const { streamers, disk, connected } = useWebSocket(token)

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: Infinity,
  })

  const sites = settings?.sites ?? {}

  return (
    <AppShell disk={disk} connected={connected} streamerCount={streamers.length}>
      <div className="flex flex-col gap-3 h-full">
        {/* Toolbar */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <BulkActions />
          <AddStreamerDialog sites={sites} />
          <div className="flex-1" />
          <StreamerFilters
            filters={filters}
            sites={sites}
            onFiltersChange={setFilters}
          />
        </div>

        {/* Table */}
        <div className="flex-1 min-h-0">
          <StreamerTable
            streamers={streamers}
            filters={filters}
          />
        </div>
      </div>
    </AppShell>
  )
}
