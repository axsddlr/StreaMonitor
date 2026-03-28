import { useMemo, useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  MoreHorizontal,
  Trash2,
  Video,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Circle,
  Loader2,
  ExternalLink,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { StatusBadge } from './StatusBadge'
import { toggleStreamer, removeStreamer } from '@/api/client'
import { cn, formatBytes } from '@/lib/utils'
import type { StreamerDTO } from '@/lib/types'
import type { FilterState } from './StreamerFilters'

interface StreamerTableProps {
  streamers: StreamerDTO[]
  filters: FilterState
  isLoading?: boolean
}

interface RemoveTarget {
  username: string
  site: string
}

const columnHelper = createColumnHelper<StreamerDTO>()

export function StreamerTable({ streamers, filters, isLoading = false }: StreamerTableProps) {
  const queryClient = useQueryClient()
  const [sorting, setSorting] = useState<SortingState>([])
  const [removeTarget, setRemoveTarget] = useState<RemoveTarget | null>(null)
  const [togglingKey, setTogglingKey] = useState<string | null>(null)

  const toggleMutation = useMutation({
    mutationFn: ({ username, site }: { username: string; site: string }) =>
      toggleStreamer(username, site),
    onMutate: ({ username, site }) => {
      setTogglingKey(`${username}:${site}`)
    },
    onSuccess: (data, { username }) => {
      toast.success(`${username} ${data.running ? 'started' : 'stopped'}`)
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
    },
    onError: (err: Error) => {
      toast.error(`Toggle failed: ${err.message}`)
    },
    onSettled: () => {
      setTogglingKey(null)
    },
  })

  const removeMutation = useMutation({
    mutationFn: ({ username, site }: { username: string; site: string }) =>
      removeStreamer(username, site),
    onSuccess: (data, { username }) => {
      toast.success(data.message || `Removed ${username}`)
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
      setRemoveTarget(null)
    },
    onError: (err: Error) => {
      toast.error(`Remove failed: ${err.message}`)
      setRemoveTarget(null)
    },
  })

  const handleToggle = useCallback(
    (username: string, site: string) => {
      toggleMutation.mutate({ username, site })
    },
    [toggleMutation]
  )

  const handleRemoveConfirm = useCallback(() => {
    if (removeTarget) {
      removeMutation.mutate(removeTarget)
    }
  }, [removeTarget, removeMutation])

  const columns = useMemo(
    () => [
      columnHelper.accessor('status_code', {
        header: 'Status',
        cell: (info) => (
          <StatusBadge
            status_code={info.getValue()}
            status_text={info.row.original.status_text}
          />
        ),
        size: 110,
      }),
      columnHelper.accessor('username', {
        header: 'Username',
        cell: (info) => {
          const row = info.row.original
          return (
            <div className="flex items-center gap-1.5 min-w-0">
              {row.country_flag && (
                <span className="text-sm shrink-0" title={row.country_name} aria-label={row.country_name}>
                  {row.country_flag}
                </span>
              )}
              <Link
                to={`/recordings/${encodeURIComponent(row.username)}/${encodeURIComponent(row.site)}`}
                className="text-sm font-medium text-foreground hover:text-blue-400 hover:underline truncate transition-colors duration-150"
                title={`View recordings for ${row.username}`}
              >
                {info.getValue()}
              </Link>
              {row.url && (
                <a
                  href={row.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-foreground shrink-0"
                  title="Open stream"
                  aria-label={`Open ${row.username}'s stream`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          )
        },
        size: 180,
      }),
      columnHelper.accessor('site', {
        header: 'Site',
        cell: (info) => (
          <span className="text-xs text-muted-foreground">
            {info.row.original.site}
          </span>
        ),
        size: 120,
      }),
      columnHelper.accessor('running', {
        header: 'Running',
        cell: (info) => {
          const row = info.row.original
          const key = `${row.username}:${row.site}`
          const isToggling = togglingKey === key

          return (
            <button
              type="button"
              role="switch"
              aria-checked={row.running}
              aria-label={`${row.running ? 'Stop' : 'Start'} monitoring ${row.username}`}
              disabled={isToggling}
              onClick={() => handleToggle(row.username, row.site)}
              className={cn(
                'relative inline-flex h-4 w-8 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                row.running
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-secondary hover:bg-secondary/80',
                isToggling && 'opacity-50 cursor-not-allowed'
              )}
            >
              {isToggling ? (
                <Loader2 className="absolute left-1/2 -translate-x-1/2 h-2.5 w-2.5 animate-spin text-white" />
              ) : (
                <span
                  className={cn(
                    'inline-block h-3 w-3 rounded-full bg-white shadow-sm transition-transform',
                    row.running ? 'translate-x-4' : 'translate-x-0.5'
                  )}
                />
              )}
            </button>
          )
        },
        size: 80,
      }),
      columnHelper.accessor('recording', {
        header: 'Rec',
        cell: (info) => (
          <span
            className="flex items-center"
            title={info.getValue() ? 'Recording' : 'Not recording'}
            aria-label={info.getValue() ? 'Recording active' : 'Not recording'}
          >
            {info.getValue() ? (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-glow-ring" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500 animate-rec-blink" />
              </span>
            ) : (
              <Circle className="h-2 w-2 fill-transparent text-muted-foreground/20" />
            )}
          </span>
        ),
        size: 50,
      }),
      columnHelper.accessor('video_count', {
        header: 'Videos',
        cell: (info) => {
          const row = info.row.original
          return (
            <span className="text-xs text-muted-foreground tabular-nums">
              {info.getValue()}
              {row.video_total_size > 0 && (
                <span className="ml-1 text-muted-foreground/60">
                  ({formatBytes(row.video_total_size)})
                </span>
              )}
            </span>
          )
        },
        size: 120,
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => {
          const row = info.row.original
          const key = `${row.username}:${row.site}`
          const isToggling = togglingKey === key

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  aria-label={`Actions for ${row.username}`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem
                  onClick={() => handleToggle(row.username, row.site)}
                  disabled={isToggling}
                >
                  {row.running ? (
                    <>Stop monitoring</>
                  ) : (
                    <>Start monitoring</>
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to={`/recordings/${encodeURIComponent(row.username)}/${encodeURIComponent(row.site)}`}>
                    <Video className="h-4 w-4" />
                    View recordings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => setRemoveTarget({ username: row.username, site: row.site })}
                >
                  <Trash2 className="h-4 w-4" />
                  Remove
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
        size: 48,
      }),
    ],
    [handleToggle, togglingKey]
  )

  const filteredData = useMemo(() => {
    return streamers.filter((s) => {
      if (filters.username && !s.username.toLowerCase().includes(filters.username.toLowerCase())) {
        return false
      }
      if (filters.site && s.siteslug !== filters.site) {
        return false
      }
      if (filters.status && s.status_code.toString() !== filters.status) {
        return false
      }
      return true
    })
  }, [streamers, filters])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <>
      <div className="rounded-md overflow-hidden" style={{ border: '1px solid hsl(var(--border))', background: 'hsl(var(--card))' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="grid" aria-label="Streamers list">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-border" style={{ background: 'hsl(var(--secondary) / 0.4)' }}>
                  {headerGroup.headers.map((header) => {
                    const canSort = header.column.getCanSort()
                    const sortDir = header.column.getIsSorted()

                    return (
                      <th
                        key={header.id}
                        scope="col"
                        className={cn(
                          'px-3 py-1.5 text-left text-[11px] font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap',
                          canSort && 'cursor-pointer select-none hover:text-foreground transition-colors duration-150'
                        )}
                        style={{ width: header.getSize() }}
                        onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                        aria-sort={
                          sortDir === 'asc'
                            ? 'ascending'
                            : sortDir === 'desc'
                            ? 'descending'
                            : undefined
                        }
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {canSort && (
                            <span className="ml-0.5 opacity-50">
                              {sortDir === 'asc' ? (
                                <ChevronUp className="h-3 w-3" />
                              ) : sortDir === 'desc' ? (
                                <ChevronDown className="h-3 w-3" />
                              ) : (
                                <ChevronsUpDown className="h-3 w-3" />
                              )}
                            </span>
                          )}
                        </div>
                      </th>
                    )
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-3 py-8 text-center text-sm text-muted-foreground"
                  >
                    <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                    Loading streamers...
                  </td>
                </tr>
              ) : table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-3 py-8 text-center text-sm text-muted-foreground"
                  >
                    {streamers.length === 0
                      ? 'No streamers added yet. Use the Add Streamer button to get started.'
                      : 'No streamers match the current filters.'}
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-border/40 hover:bg-white/[0.03] transition-colors duration-100"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="px-3 py-1 align-middle"
                        style={{ width: cell.column.getSize() }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!isLoading && filteredData.length > 0 && (
          <div className="px-3 py-1 border-t border-border/40" style={{ background: 'hsl(var(--secondary) / 0.2)' }}>
            <span className="text-[11px] text-muted-foreground tabular-nums">
              {filteredData.length} streamer{filteredData.length !== 1 ? 's' : ''}
              {filteredData.length !== streamers.length && ` (filtered from ${streamers.length})`}
            </span>
          </div>
        )}
      </div>

      <Dialog
        open={removeTarget !== null}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove Streamer</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove{' '}
              <strong>{removeTarget?.username}</strong> from{' '}
              <strong>{removeTarget?.site}</strong>? This will stop monitoring and
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRemoveTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleRemoveConfirm}
              disabled={removeMutation.isPending}
            >
              {removeMutation.isPending && (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              )}
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
