import { useState, useEffect, useRef, useCallback } from 'react'
import type { DiskSpaceDTO, StreamerDTO, WebSocketMessage } from '@/lib/types'
import { setToken } from '@/api/client'

const INITIAL_RECONNECT_DELAY = 1000
const MAX_RECONNECT_DELAY = 30000
const RECONNECT_MULTIPLIER = 2

export interface UseWebSocketReturn {
  streamers: StreamerDTO[]
  disk: DiskSpaceDTO | null
  connected: boolean
}

export function useWebSocket(token: string | null): UseWebSocketReturn {
  const [streamers, setStreamers] = useState<StreamerDTO[]>([])
  const [disk, setDisk] = useState<DiskSpaceDTO | null>(null)
  const [connected, setConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMountedRef = useRef(true)

  const buildWsUrl = useCallback((): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${protocol}//${host}/ws/status${tokenParam}`
  }, [token])

  const connect = useCallback((): void => {
    if (!isMountedRef.current) return

    const url = buildWsUrl()
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!isMountedRef.current) return
      setConnected(true)
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
    }

    ws.onmessage = (event: MessageEvent) => {
      if (!isMountedRef.current) return
      try {
        const data = JSON.parse(event.data as string) as WebSocketMessage
        setStreamers(data.streamers)
        setDisk(data.disk)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = (event: CloseEvent) => {
      if (!isMountedRef.current) return
      setConnected(false)
      wsRef.current = null

      // The auth guard rejects a bad/stale token before the WS handshake
      // completes (HTTP 401/403), which the browser only ever surfaces as a
      // generic abnormal close (code 1006) — there's no clean 4001 to check.
      // Retrying forever with the same dead token just spams reconnects, so
      // once the token is known-bad, confirm via a REST call and force
      // re-login instead of continuing the backoff loop.
      if (event.code === 1006 && token) {
        void fetch(`/api/v1/system/settings`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => {
          if (res.status === 401 || res.status === 403) {
            setToken(null)
            window.location.href = '/login'
          } else if (isMountedRef.current) {
            scheduleReconnect()
          }
        }).catch(() => {
          if (isMountedRef.current) scheduleReconnect()
        })
        return
      }

      scheduleReconnect()
    }

    function scheduleReconnect(): void {
      const delay = reconnectDelayRef.current
      reconnectDelayRef.current = Math.min(
        delay * RECONNECT_MULTIPLIER,
        MAX_RECONNECT_DELAY
      )

      reconnectTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          connect()
        }
      }, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [buildWsUrl])

  useEffect(() => {
    isMountedRef.current = true

    if (token !== null) {
      connect()
    }

    return () => {
      isMountedRef.current = false

      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }

      if (wsRef.current !== null) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }

      setConnected(false)
    }
  }, [token, connect])

  return { streamers, disk, connected }
}
