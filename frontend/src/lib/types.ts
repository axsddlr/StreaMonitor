export interface StreamerDTO {
  username: string
  site: string
  siteslug: string
  running: boolean
  recording: boolean
  status_code: number
  status_text: string
  url: string
  gender: string | null
  country: string | null
  country_flag: string
  country_name: string
  video_count: number
  video_total_size: number
}

export interface RecordingDTO {
  filename: string
  filesize: number
  filesize_human: string
  abs_path: string
}

export interface DiskSpaceDTO {
  free: number
  total: number
  free_human: string
  total_human: string
  percentage_free: number
}

export interface SettingsDTO {
  sites: Record<string, string>
  statuses: Record<string, string>
}

export interface StreamersResponse {
  streamers: StreamerDTO[]
  disk: DiskSpaceDTO
}

export interface StreamerFilters {
  filter_username?: string
  filter_site?: string
  filter_status?: string
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}

export interface RecordingsResponse {
  streamer: StreamerDTO
  recordings: RecordingDTO[]
  total_size: number
  total_size_human: string
}

export interface ApiResponse {
  message: string
  success?: boolean
}

export interface ToggleResponse {
  message: string
  running: boolean
}

export interface LoginResponse {
  token: string
}

export interface WebSocketMessage {
  streamers: StreamerDTO[]
  disk: DiskSpaceDTO
}
