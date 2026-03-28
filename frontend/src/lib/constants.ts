export interface StatusConfig {
  label: string
  colorClass: string
  badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline'
  dotClass: string
  /** If true, render a pulsing halo — used for live/active states */
  pulse: boolean
}

export const STATUS_CONFIG: Record<number, StatusConfig> = {
  200: {
    label: 'Online',
    colorClass: 'text-emerald-400',
    badgeVariant: 'outline',
    dotClass: 'bg-emerald-400',
    pulse: true,
  },
  404: {
    label: 'Offline',
    colorClass: 'text-slate-400',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-500',
    pulse: false,
  },
  410: {
    label: 'Offline',
    colorClass: 'text-slate-400',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-500',
    pulse: false,
  },
  403: {
    label: 'Private',
    colorClass: 'text-violet-400',
    badgeVariant: 'outline',
    dotClass: 'bg-violet-400',
    pulse: false,
  },
  2: {
    label: 'Not Running',
    colorClass: 'text-slate-500',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-600',
    pulse: false,
  },
  429: {
    label: 'Rate Limited',
    colorClass: 'text-amber-400',
    badgeVariant: 'outline',
    dotClass: 'bg-amber-400',
    pulse: false,
  },
  400: {
    label: 'Not Found',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-500',
    pulse: false,
  },
  3: {
    label: 'Error',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-500',
    pulse: false,
  },
  1403: {
    label: 'Restricted',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-500',
    pulse: false,
  },
  1: {
    label: 'Unknown',
    colorClass: 'text-yellow-400',
    badgeVariant: 'outline',
    dotClass: 'bg-yellow-400',
    pulse: false,
  },
}

export const DEFAULT_STATUS_CONFIG: StatusConfig = {
  label: 'Unknown',
  colorClass: 'text-yellow-400',
  badgeVariant: 'outline',
  dotClass: 'bg-yellow-400',
  pulse: false,
}

export const getStatusConfig = (statusCode: number): StatusConfig => {
  return STATUS_CONFIG[statusCode] ?? DEFAULT_STATUS_CONFIG
}
