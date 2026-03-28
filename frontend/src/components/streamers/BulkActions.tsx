import { useState } from 'react'
import { Play, Square, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { startAll, stopAll } from '@/api/client'

type ActionType = 'start' | 'stop' | null

export function BulkActions() {
  const [pendingAction, setPendingAction] = useState<ActionType>(null)
  const queryClient = useQueryClient()

  const startMutation = useMutation({
    mutationFn: startAll,
    onSuccess: (data) => {
      toast.success(data.message || 'All streamers started')
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
    },
    onError: (err: Error) => {
      toast.error(`Failed to start all: ${err.message}`)
    },
  })

  const stopMutation = useMutation({
    mutationFn: stopAll,
    onSuccess: (data) => {
      toast.success(data.message || 'All streamers stopped')
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
    },
    onError: (err: Error) => {
      toast.error(`Failed to stop all: ${err.message}`)
    },
  })

  const isLoading = startMutation.isPending || stopMutation.isPending

  function handleConfirm() {
    if (pendingAction === 'start') {
      startMutation.mutate()
    } else if (pendingAction === 'stop') {
      stopMutation.mutate()
    }
    setPendingAction(null)
  }

  return (
    <>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          className="h-8 text-xs"
          onClick={() => setPendingAction('start')}
          disabled={isLoading}
          aria-label="Start all streamers"
        >
          {startMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Start All
        </Button>

        <Button
          variant="secondary"
          size="sm"
          className="h-8 text-xs"
          onClick={() => setPendingAction('stop')}
          disabled={isLoading}
          aria-label="Stop all streamers"
        >
          {stopMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Square className="h-3.5 w-3.5" />
          )}
          Stop All
        </Button>
      </div>

      <Dialog open={pendingAction !== null} onOpenChange={(open) => !open && setPendingAction(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {pendingAction === 'start' ? 'Start All Streamers' : 'Stop All Streamers'}
            </DialogTitle>
            <DialogDescription>
              {pendingAction === 'start'
                ? 'This will start monitoring all streamers that are currently not running. Continue?'
                : 'This will stop monitoring all currently running streamers. Continue?'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setPendingAction(null)}>
              Cancel
            </Button>
            <Button
              variant={pendingAction === 'stop' ? 'destructive' : 'default'}
              size="sm"
              onClick={handleConfirm}
            >
              {pendingAction === 'start' ? 'Start All' : 'Stop All'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
