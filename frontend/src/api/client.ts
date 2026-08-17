import type {
  ApiResponse,
  DiskSpaceDTO,
  LoginResponse,
  RecordingsResponse,
  SettingsDTO,
  StreamerFilters,
  StreamersResponse,
  ToggleResponse,
} from '@/lib/types'

const BASE_URL = ''
const TOKEN_KEY = 'streamonitor_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token === null) {
    localStorage.removeItem(TOKEN_KEY)
  } else {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`
    try {
      const errorBody = await response.json() as { detail?: string; message?: string }
      errorMessage = errorBody.detail ?? errorBody.message ?? errorMessage
    } catch {
      // ignore json parse errors on error responses
    }
    if (response.status === 401 && token) {
      setToken(null)
      window.location.href = '/login'
    }
    throw new Error(errorMessage)
  }

  return response.json() as Promise<T>
}

export async function login(password: string): Promise<LoginResponse> {
  const credentials = btoa(`admin:${password}`)
  const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: 'GET',
    headers: {
      Authorization: `Basic ${credentials}`,
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Invalid password')
    }
    throw new Error(`Login failed: ${response.statusText}`)
  }

  return response.json() as Promise<LoginResponse>
}

export async function getSettings(): Promise<SettingsDTO> {
  return apiFetch<SettingsDTO>('/api/v1/system/settings')
}

export async function getDiskSpace(): Promise<DiskSpaceDTO> {
  return apiFetch<DiskSpaceDTO>('/api/v1/system/disk-space')
}

export async function getStreamers(filters?: StreamerFilters): Promise<StreamersResponse> {
  const params = new URLSearchParams()
  if (filters?.filter_username) params.set('filter_username', filters.filter_username)
  if (filters?.filter_site) params.set('filter_site', filters.filter_site)
  if (filters?.filter_status) params.set('filter_status', filters.filter_status)
  if (filters?.sort_by) params.set('sort_by', filters.sort_by)
  if (filters?.sort_dir) params.set('sort_dir', filters.sort_dir)

  const query = params.toString()
  return apiFetch<StreamersResponse>(`/api/v1/streamers${query ? `?${query}` : ''}`)
}

export async function addStreamer(username: string, site: string): Promise<ApiResponse> {
  return apiFetch<ApiResponse>('/api/v1/streamers', {
    method: 'POST',
    body: JSON.stringify({ username, site }),
  })
}

export async function removeStreamer(username: string, site: string): Promise<ApiResponse> {
  return apiFetch<ApiResponse>(`/api/v1/streamers/${encodeURIComponent(username)}/${encodeURIComponent(site)}`, {
    method: 'DELETE',
  })
}

export async function toggleStreamer(username: string, site: string): Promise<ToggleResponse> {
  return apiFetch<ToggleResponse>(`/api/v1/streamers/${encodeURIComponent(username)}/${encodeURIComponent(site)}/toggle`, {
    method: 'PATCH',
  })
}

export async function setCookies(username: string, site: string, content: string): Promise<{ message: string; cookies_path: string | null }> {
  return apiFetch<{ message: string; cookies_path: string | null }>(`/api/v1/streamers/${encodeURIComponent(username)}/${encodeURIComponent(site)}/cookies`, {
    method: 'PATCH',
    body: JSON.stringify({ content }),
  })
}

export async function startAll(): Promise<ApiResponse> {
  return apiFetch<ApiResponse>('/api/v1/streamers/start-all', {
    method: 'PATCH',
  })
}

export async function stopAll(): Promise<ApiResponse> {
  return apiFetch<ApiResponse>('/api/v1/streamers/stop-all', {
    method: 'PATCH',
  })
}

export async function getRecordings(username: string, site: string): Promise<RecordingsResponse> {
  return apiFetch<RecordingsResponse>(`/api/v1/streamers/${encodeURIComponent(username)}/${encodeURIComponent(site)}/recordings`)
}

export async function deleteRecording(username: string, site: string, filename: string): Promise<ApiResponse> {
  return apiFetch<ApiResponse>(`/api/v1/streamers/${encodeURIComponent(username)}/${encodeURIComponent(site)}/recordings/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  })
}

export function getVideoUrl(username: string, site: string, filename: string): string {
  const token = getToken()
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${BASE_URL}/api/v1/video/${encodeURIComponent(username)}/${encodeURIComponent(site)}/${encodeURIComponent(filename)}${tokenParam}`
}
