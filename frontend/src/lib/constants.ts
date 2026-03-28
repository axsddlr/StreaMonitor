export interface StatusConfig {
  label: string
  colorClass: string
  badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline'
  dotClass: string
}

export const STATUS_CONFIG: Record<number, StatusConfig> = {
  200: {
    label: 'Online',
    colorClass: 'text-green-400',
    badgeVariant: 'outline',
    dotClass: 'bg-green-400',
  },
  404: {
    label: 'Offline',
    colorClass: 'text-slate-400',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-400',
  },
  410: {
    label: 'Offline',
    colorClass: 'text-slate-400',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-400',
  },
  403: {
    label: 'Private',
    colorClass: 'text-purple-400',
    badgeVariant: 'outline',
    dotClass: 'bg-purple-400',
  },
  2: {
    label: 'Not Running',
    colorClass: 'text-slate-500',
    badgeVariant: 'secondary',
    dotClass: 'bg-slate-500',
  },
  429: {
    label: 'Rate Limited',
    colorClass: 'text-orange-400',
    badgeVariant: 'outline',
    dotClass: 'bg-orange-400',
  },
  400: {
    label: 'Not Found',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-400',
  },
  3: {
    label: 'Error',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-400',
  },
  1403: {
    label: 'Restricted',
    colorClass: 'text-red-400',
    badgeVariant: 'destructive',
    dotClass: 'bg-red-400',
  },
  1: {
    label: 'Unknown',
    colorClass: 'text-yellow-400',
    badgeVariant: 'outline',
    dotClass: 'bg-yellow-400',
  },
}

export const DEFAULT_STATUS_CONFIG: StatusConfig = {
  label: 'Unknown',
  colorClass: 'text-yellow-400',
  badgeVariant: 'outline',
  dotClass: 'bg-yellow-400',
}

export const getStatusConfig = (statusCode: number): StatusConfig => {
  return STATUS_CONFIG[statusCode] ?? DEFAULT_STATUS_CONFIG
}
