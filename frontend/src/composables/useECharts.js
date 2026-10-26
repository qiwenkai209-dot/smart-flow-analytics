/**
 * ECharts 实例管理 Hook
 * 自动响应容器大小变化（ResizeObserver）
 */
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import * as echarts from 'echarts'

export function useECharts(containerRef) {
  const chart = shallowRef(null)
  let observer = null

  function init(theme = null) {
    if (!containerRef.value) return
    chart.value = echarts.init(containerRef.value, theme, { renderer: 'canvas' })
    observer = new ResizeObserver(() => chart.value?.resize())
    observer.observe(containerRef.value)
  }

  function setOption(option) {
    chart.value?.setOption(option, { notMerge: false, lazyUpdate: true })
  }

  onMounted(() => init())
  onUnmounted(() => {
    observer?.disconnect()
    chart.value?.dispose()
  })

  return { chart, setOption }
}
