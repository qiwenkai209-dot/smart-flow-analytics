/**
 * WebSocket 实时数据 Hook
 * 自动连接、断线重连、心跳保持
 */
import { ref, onMounted, onUnmounted } from 'vue'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/realtime'
const RECONNECT_DELAY = 3000

export function useRealtimeData() {
  const data = ref({
    current_in_venue: 0,
    total_in_today: 0,
    total_out_today: 0,
    gender: { male: 0, female: 0 },
    age_group: { child: 0, young: 0, adult: 0, elder: 0 },
    zone_dwell: [],
  })
  const connected = ref(false)
  let ws = null
  let reconnectTimer = null

  function connect() {
    if (ws) ws.close()
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      connected.value = true
      console.log('WebSocket 已连接')
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    }

    ws.onmessage = (evt) => {
      try { data.value = JSON.parse(evt.data) } catch (e) { /* ignore */ }
    }

    ws.onclose = () => {
      connected.value = false
      console.log(`WebSocket 断开，${RECONNECT_DELAY / 1000}s 后重连...`)
      reconnectTimer = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => ws.close()
  }

  onMounted(connect)
  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (ws) ws.close()
  })

  return { data, connected }
}
