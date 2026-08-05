import { useState, useEffect } from 'react'
import { Share2, Clipboard, Check, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { createShareLink, listShareLinks, revokeShareLink } from '@/api/share'
import type { ShareTokenItem } from '@/types/share'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  seriesId: string
  seriesTitle?: string
  visibleUntilOrder: number
}

export function ShareDialog({
  open,
  onOpenChange,
  seriesId,
  seriesTitle,
  visibleUntilOrder,
}: Props) {
  const [createdUrl, setCreatedUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)
  const [links, setLinks] = useState<ShareTokenItem[]>([])
  const [fetchingLinks, setFetchingLinks] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<ShareTokenItem | null>(null)
  const [revoking, setRevoking] = useState(false)

  function handleOpenChange(newOpen: boolean) {
    if (!newOpen) {
      setCreatedUrl(null)
      setCopied(false)
      setRevokeTarget(null)
    }
    onOpenChange(newOpen)
  }

  useEffect(() => {
    if (open) {
      void fetchLinks()
    }
  }, [open])


  async function fetchLinks() {
    setFetchingLinks(true)
    try {
      const items = await listShareLinks()
      setLinks(items)
    } catch {
      // Best-effort list fetch
    } finally {
      setFetchingLinks(false)
    }
  }

  async function handleCreate() {
    setLoading(true)
    try {
      const res = await createShareLink(seriesId, visibleUntilOrder)
      const fullUrl = `${window.location.origin}${res.url}`
      setCreatedUrl(fullUrl)
      fetchLinks()
    } catch {
      // Failed to create
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy() {
    if (!createdUrl) return
    try {
      await navigator.clipboard.writeText(createdUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard write failed
    }
  }

  async function handleConfirmRevoke() {
    if (!revokeTarget) return
    setRevoking(true)
    try {
      await revokeShareLink(revokeTarget.token_hash)
      setLinks((prev) => prev.filter((item) => item.id !== revokeTarget.id))
      setRevokeTarget(null)
    } catch {
      // Failed to revoke
    } finally {
      setRevoking(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>

        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-heading text-xl">
              <Share2 className="h-5 w-5 text-accent" />
              Share snapshot
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              Snapshot of {seriesTitle || seriesId} · visible through episode{' '}
              {visibleUntilOrder}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {!createdUrl ? (
              <Button
                type="button"
                className="w-full bg-primary text-primary-foreground min-h-[44px]"
                onClick={handleCreate}
                disabled={loading}
              >
                {loading ? 'Creating...' : 'Create share link'}
              </Button>
            ) : (
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">
                  Shareable link
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    readOnly
                    value={createdUrl}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground [color-scheme:dark]"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    className="min-h-[44px] shrink-0"
                    onClick={handleCopy}
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-accent" />
                        <span className="text-xs">Copied</span>
                      </>
                    ) : (
                      <>
                        <Clipboard className="h-4 w-4" />
                        <span className="text-xs">Copy</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            <div className="space-y-2 pt-2 border-t border-border">
              <h4 className="text-xs font-medium uppercase text-muted-foreground">
                Active share links
              </h4>
              {fetchingLinks ? (
                <p className="text-xs text-muted-foreground">Loading active links...</p>
              ) : links.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No active snapshot links.
                </p>
              ) : (
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {links.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between gap-2 rounded-md bg-muted/50 px-3 py-2 text-xs"
                    >
                      <div className="truncate">
                        <span className="font-medium text-foreground">
                          Episode {item.visible_until_order}
                        </span>{' '}
                        <span className="text-muted-foreground">
                          · expires {new Date(item.expires_at * 1000).toLocaleDateString()}
                        </span>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 px-2"
                        onClick={() => setRevokeTarget(item)}
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Revoke
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Revoke confirmation modal */}
      <Dialog open={!!revokeTarget} onOpenChange={() => setRevokeTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Revoke link</DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              Revoking this link makes it stop working for everyone who has it.
              This can't be undone. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setRevokeTarget(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleConfirmRevoke}
              disabled={revoking}
            >
              {revoking ? 'Revoking...' : 'Revoke link'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
