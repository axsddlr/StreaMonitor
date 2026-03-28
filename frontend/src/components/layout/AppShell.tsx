import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Wifi, WifiOff } from 'lucide-react'
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
        className="flex flex-col w-14 shrink-0 border-r border-border bg-[hsl(var(--sidebar-background))]"
        aria-label="Main navigation"
      >
        {/* Logo area */}
        <div className="flex items-center justify-center h-12 border-b border-border shrink-0">
          <span className="text-primary font-bold text-lg" aria-label="StreaMonitor">
            SM
          </span>
        </div>

        {/* Nav items */}
        <nav className="flex flex-col items-center gap-1 py-2 flex-1" aria-label="Navigation">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              cn(
                'flex items-center justify-center h-10 w-10 rounded-md transition-colors',
                'hover:bg-[hsl(var(--sidebar-accent))] text-[hsl(var(--sidebar-foreground))]',
                isActive && 'bg-[hsl(var(--sidebar-accent))] text-[hsl(var(--sidebar-primary))]'
              )
            }
            title="Dashboard"
            aria-label="Dashboard"
          >
            <LayoutDashboard className="h-5 w-5" />
          </NavLink>
        </nav>

        {/* Connection indicator */}
        <div className="flex items-center justify-center pb-3 shrink-0">
          <span
            title={connected ? 'Live feed connected' : 'Live feed disconnected'}
            aria-label={connected ? 'Connected' : 'Disconnected'}
          >
            {connected ? (
              <Wifi className="h-4 w-4 text-green-400" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-400 animate-pulse" />
            )}
          </span>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between h-12 px-4 shrink-0 border-b border-border bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold text-foreground whitespace-nowrap">
              StreaMonitor
            </h1>
            {streamerCount !== undefined && (
              <span className="text-xs text-muted-foreground">
                {streamerCount} streamer{streamerCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <DiskSpaceBar disk={disk} className="shrink-0" />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 min-h-0" id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}
