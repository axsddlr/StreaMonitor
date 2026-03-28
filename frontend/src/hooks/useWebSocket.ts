import { useState, useEffect, useRef, useCallback } from 'react'
import type { DiskSpaceDTO, StreamerDTO, WebSocketMessage } from '@/lib/types'

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

    ws.onclose = () => {
      if (!isMountedRef.current) return
      setConnected(false)
      wsRef.current = null

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
