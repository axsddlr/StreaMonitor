import { useState, useCallback } from 'react'
import { Plus, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { addStreamer } from '@/api/client'

interface AddStreamerDialogProps {
  sites: Record<string, string>
}

export function AddStreamerDialog({ sites }: AddStreamerDialogProps) {
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [site, setSite] = useState('')
  const queryClient = useQueryClient()

  const siteEntries = Object.entries(sites)

  const mutation = useMutation({
    mutationFn: ({ username, site }: { username: string; site: string }) =>
      addStreamer(username, site),
    onSuccess: (data) => {
      toast.success(data.message || `Added ${username}`)
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
      setOpen(false)
      setUsername('')
      setSite('')
    },
    onError: (err: Error) => {
      toast.error(`Failed to add streamer: ${err.message}`)
    },
  })

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!username.trim() || !site) return
      mutation.mutate({ username: username.trim(), site })
    },
    [username, site, mutation]
  )

  const handleOpenChange = useCallback((isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) {
      setUsername('')
      setSite('')
      mutation.reset()
    }
  }, [mutation])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8 text-xs" aria-label="Add new streamer">
          <Plus className="h-3.5 w-3.5" />
          Add Streamer
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Add Streamer</DialogTitle>
          <DialogDescription>
            Enter the username and site to start monitoring a new streamer.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-3 py-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-username" className="text-sm font-medium">
                Username
              </label>
              <Input
                id="add-username"
                type="text"
                placeholder="e.g. streamer_name"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="off"
                autoFocus
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-site" className="text-sm font-medium">
                Site
              </label>
              <Select value={site} onValueChange={setSite} required>
                <SelectTrigger id="add-site">
                  <SelectValue placeholder="Select site..." />
                </SelectTrigger>
                <SelectContent>
                  {siteEntries.map(([slug, name]) => (
                    <SelectItem key={slug} value={slug}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="mt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={mutation.isPending || !username.trim() || !site}
            >
              {mutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Add
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
