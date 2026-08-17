import { useState, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
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
import { Textarea } from '@/components/ui/textarea'
import { setCookies } from '@/api/client'

interface CookiesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  username: string
  site: string
  cookiesPath: string | null
}

export function CookiesDialog({ open, onOpenChange, username, site, cookiesPath }: CookiesDialogProps) {
  const [content, setContent] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: ({ content }: { content: string }) => setCookies(username, site, content),
    onSuccess: (data) => {
      toast.success(data.message)
      void queryClient.invalidateQueries({ queryKey: ['streamers'] })
      onOpenChange(false)
    },
    onError: (err: Error) => {
      toast.error(`Failed to save cookies: ${err.message}`)
    },
  })

  const handleSave = useCallback(() => {
    mutation.mutate({ content })
  }, [content, mutation])

  const handleClear = useCallback(() => {
    mutation.mutate({ content: '' })
  }, [mutation])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Account Cookies</DialogTitle>
          <DialogDescription>
            Paste a Netscape <code className="text-xs">cookies.txt</code> export (from a browser
            extension like "Get cookies.txt LOCALLY") for <strong>{username}</strong> to record
            private shows with your account. Leave empty and save to clear.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 py-2">
          {cookiesPath && (
            <p className="text-xs text-muted-foreground">
              Cookies are currently set. Pasting new content will replace them.
            </p>
          )}
          <Textarea
            id="cookies-content"
            placeholder="# Netscape HTTP Cookie File&#10;.chaturbate.com&#9;TRUE&#9;/&#9;TRUE&#9;0&#9;csb&#9;abc123"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
            className="font-mono text-xs h-56"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {cookiesPath && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleClear}
              disabled={mutation.isPending}
            >
              Clear
            </Button>
          )}
          <Button size="sm" onClick={handleSave} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
