import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DiskSpaceBar } from '@/components/system/DiskSpaceBar'
import type { DiskSpaceDTO } from '@/lib/types'

interface AppShellProps {
  children: ReactNode
  disk: DiskSpaceDTO | null
  connected: boolean
  streamerCount?: number
}

export function AppShell({ children, disk, connected, streamerCount }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className="flex flex-col w-14 shrink-0 border-r border-border"
        style={{ background: 'hsl(var(--sidebar-background))' }}
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="flex items-center justify-center h-12 border-b border-border shrink-0">
          <span
            className="font-bold text-base tracking-tight"
            style={{ color: 'hsl(var(--sidebar-primary))' }}
            aria-label="StreaMonitor"
          >
            SM
          </span>
        </div>

        {/* Nav */}
        <nav className="flex flex-col items-center gap-1 py-2 flex-1" aria-label="Navigation">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              cn(
                'flex items-center justify-center h-9 w-9 rounded-md transition-colors duration-150',
                isActive
                  ? 'text-blue-400 bg-blue-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              )
            }
            title="Dashboard"
            aria-label="Dashboard"
          >
            <LayoutDashboard className="h-4 w-4" />
          </NavLink>
        </nav>

        {/* Live connection indicator */}
        <div className="flex items-center justify-center pb-4 shrink-0">
          <span
            className="relative flex h-2 w-2"
            title={connected ? 'Live feed connected' : 'Live feed disconnected'}
            aria-label={connected ? 'Connected' : 'Disconnected'}
          >
            {connected && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-glow-ring" />
            )}
            <span
              className={cn(
                'relative inline-flex rounded-full h-2 w-2 transition-colors duration-300',
                connected ? 'bg-emerald-400' : 'bg-slate-600'
              )}
            />
          </span>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        {/* Header */}
        <header
          className="flex items-center justify-between h-11 px-4 shrink-0 border-b border-border"
          style={{ background: 'hsl(var(--background) / 0.9)', backdropFilter: 'blur(8px)' }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-sm font-semibold text-foreground whitespace-nowrap font-mono tracking-tight">
              StreaMonitor
            </span>
            {streamerCount !== undefined && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {streamerCount} streamer{streamerCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <DiskSpaceBar disk={disk} className="shrink-0" />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-3 min-h-0" id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}
