import { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowLeft,
  Trash2,
  Play,
  X,
  Loader2,
  HardDrive,
  FileVideo,
} from 'lucide-react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { StatusBadge } from '@/components/streamers/StatusBadge'
import { getRecordings, deleteRecording, getVideoUrl } from '@/api/client'
import { cn } from '@/lib/utils'
import type { RecordingDTO } from '@/lib/types'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'

const columnHelper = createColumnHelper<RecordingDTO>()

export function Recordings() {
  const { username, site } = useParams<{ username: string; site: string }>()
  const queryClient = useQueryClient()
  const [sorting, setSorting] = useState<SortingState>([{ id: 'filename', desc: false }])
  const [activeVideo, setActiveVideo] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const safeUsername = username ?? ''
  const safeSite = site ?? ''

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['recordings', safeUsername, safeSite],
    queryFn: () => getRecordings(safeUsername, safeSite),
    enabled: Boolean(safeUsername && safeSite),
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => deleteRecording(safeUsername, safeSite, filename),
    onSuccess: (response, filename) => {
      toast.success(response.message || `Deleted ${filename}`)
      void queryClient.invalidateQueries({ queryKey: ['recordings', safeUsername, safeSite] })
      if (activeVideo === filename) setActiveVideo(null)
      setDeleteTarget(null)
    },
    onError: (err: Error) => {
      toast.error(`Delete failed: ${err.message}`)
      setDeleteTarget(null)
    },
  })

  const handleDeleteConfirm = useCallback(() => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget)
    }
  }, [deleteTarget, deleteMutation])

  const columns = [
    columnHelper.accessor('filename', {
      header: 'Filename',
      cell: (info) => {
        const filename = info.getValue()
        const isActive = activeVideo === filename
        return (
          <button
            type="button"
            onClick={() => setActiveVideo(isActive ? null : filename)}
            className={cn(
              'text-left text-sm font-mono truncate max-w-xs hover:text-primary transition-colors',
              isActive ? 'text-primary' : 'text-foreground'
            )}
            title={`Play ${filename}`}
            aria-label={`${isActive ? 'Hide' : 'Play'} ${filename}`}
          >
            <span className="flex items-center gap-1.5">
              <FileVideo className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              {filename}
            </span>
          </button>
        )
      },
    }),
    columnHelper.accessor('filesize', {
      header: 'Size',
      cell: (info) => (
        <span className="text-xs text-muted-foreground tabular-nums">
          {info.row.original.filesize_human}
        </span>
      ),
      size: 100,
    }),
    columnHelper.display({
      id: 'actions',
      header: '',
      cell: (info) => {
        const filename = info.row.original.filename
        return (
          <div className="flex items-center gap-1 justify-end">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setActiveVideo(activeVideo === filename ? null : filename)}
              title={`Play ${filename}`}
              aria-label={`Play ${filename}`}
            >
              <Play className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => setDeleteTarget(filename)}
              title={`Delete ${filename}`}
              aria-label={`Delete ${filename}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )
      },
      size: 80,
    }),
  ]

  const table = useReactTable({
    data: data?.recordings ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const streamer = data?.streamer

  if (!safeUsername || !safeSite) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Invalid URL parameters.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-start gap-3 shrink-0">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mt-0.5"
          aria-label="Back to dashboard"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-base font-semibold text-foreground">{safeUsername}</h2>
            <span className="text-sm text-muted-foreground">{safeSite}</span>
            {streamer && (
              <>
                <StatusBadge
                  status_code={streamer.status_code}
                  status_text={streamer.status_text}
                />
                {streamer.recording && (
                  <span className="text-xs text-red-400 font-medium flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse inline-block" />
                    Recording
                  </span>
                )}
              </>
            )}
          </div>
          {data && (
            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              <HardDrive className="h-3 w-3" />
              <span>
                {data.recordings.length} file{data.recordings.length !== 1 ? 's' : ''} &middot; {data.total_size_human} total
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Video player */}
      {activeVideo && (
        <div className="shrink-0 rounded-md border border-border overflow-hidden bg-black">
          <div className="flex items-center justify-between px-3 py-2 bg-secondary/30 border-b border-border">
            <span className="text-xs font-mono text-muted-foreground truncate">
              {activeVideo}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={() => setActiveVideo(null)}
              aria-label="Close video player"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
          <video
            key={activeVideo}
            controls
            autoPlay
            className="w-full max-h-96 bg-black"
            src={getVideoUrl(safeUsername, safeSite, activeVideo)}
            aria-label={`Video player: ${activeVideo}`}
          >
            Your browser does not support HTML5 video.
          </video>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 min-h-0 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">Loading recordings...</span>
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-destructive">
              Failed to load recordings: {(error as Error).message}
            </p>
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm" aria-label={`Recordings for ${safeUsername}`}>
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-border bg-secondary/30">
                    {headerGroup.headers.map((header) => {
                      const canSort = header.column.getCanSort()
                      const sortDir = header.column.getIsSorted()
                      return (
                        <th
                          key={header.id}
                          scope="col"
                          className={cn(
                            'px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap',
                            canSort && 'cursor-pointer select-none hover:text-foreground'
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
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={3}
                      className="px-3 py-8 text-center text-sm text-muted-foreground"
                    >
                      No recordings found for this streamer.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className={cn(
                        'border-b border-border/50 hover:bg-secondary/20 transition-colors',
                        activeVideo === row.original.filename && 'bg-secondary/30'
                      )}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className="px-3 py-1.5 align-middle"
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
        )}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Recording</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete{' '}
              <strong className="font-mono text-xs break-all">{deleteTarget}</strong>?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
