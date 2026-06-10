<template>
  <div class="network-graph">
    <div ref="chartRef" style="width: 100%; height: 600px;"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'NetworkGraph',
  props: {
    nodes: { type: Array, default: () => [] },
    edges: { type: Array, default: () => [] },
    seedIds: { type: Array, default: () => [] },
    activatedNodes: { type: Array, default: () => [] },
    communityColors: { type: Array, default: () => [
      '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
      '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b0d6'
    ]}
  },
  setup(props) {
    const chartRef = ref(null)
    let chart = null

    function buildOption() {
      if (!props.nodes.length) return null

      const seedSet = new Set(props.seedIds)
      const activatedSet = new Set(props.activatedNodes)

      const nodesData = props.nodes.map(node => {
        let color, borderColor, borderWidth, shadowBlur, symbolSize

        if (seedSet.has(node.id)) {
          color = '#ff2d2d'
          borderColor = '#fff'
          borderWidth = 3
          shadowBlur = 12
          symbolSize = Math.max(20, Math.min(45, node.degree / 1.5))
        } else if (activatedSet.has(node.id)) {
          color = '#ff9800'
          borderColor = '#ffe0b2'
          borderWidth = 2
          shadowBlur = 8
          symbolSize = Math.max(8, Math.min(20, node.degree / 2.5))
        } else {
          color = props.communityColors[node.community % props.communityColors.length]
          borderColor = 'transparent'
          borderWidth = 0
          shadowBlur = 0
          symbolSize = Math.max(3, Math.min(12, node.degree / 4))
        }

        return {
          id: String(node.id),
          name: node.is_kol ? `KOL_${node.id}` : `${node.id}`,
          x: node.x,
          y: node.y,
          symbolSize,
          itemStyle: {
            color,
            borderColor,
            borderWidth,
            shadowBlur,
            shadowColor: color,
            opacity: (seedSet.size > 0 || activatedSet.size > 0)
              ? (seedSet.has(node.id) || activatedSet.has(node.id) ? 1 : 0.25)
              : (node.is_kol ? 1 : 0.7),
          },
          category: node.community,
        }
      })

      const edgesData = props.edges.map(e => {
        const srcActivated = seedSet.has(e.source) || activatedSet.has(e.source)
        const tgtActivated = seedSet.has(e.target) || activatedSet.has(e.target)
        const highlighted = srcActivated && tgtActivated
        return {
          source: String(e.source),
          target: String(e.target),
          lineStyle: {
            opacity: highlighted ? 0.6 : 0.08,
            width: highlighted ? 1.5 : 0.3,
            color: highlighted ? '#ff9800' : '#ccc',
          }
        }
      })

      return {
        tooltip: {
          formatter: (params) => {
            if (params.dataType === 'node') {
              const node = props.nodes.find(n => String(n.id) === params.data.id)
              if (!node) return ''
              const status = seedSet.has(node.id) ? '🔴 种子KOL'
                : activatedSet.has(node.id) ? '🟠 已激活'
                : node.is_kol ? '⭐ KOL(未选中)' : '普通用户'
              return `<b>${params.data.name}</b><br/>度: ${node.degree}<br/>社区: ${node.community}<br/>状态: ${status}`
            }
            return ''
          }
        },
        series: [{
          type: 'graph',
          layout: 'none',
          data: nodesData,
          edges: edgesData,
          roam: true,
          animation: true,
          animationDuration: 400,
          animationEasingUpdate: 'cubicOut',
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 2, opacity: 0.8 }
          },
        }]
      }
    }

    function renderChart() {
      if (!chart) return
      const option = buildOption()
      if (option) {
        chart.setOption(option, { replaceMerge: ['series'] })
      }
    }

    onMounted(() => {
      chart = echarts.init(chartRef.value)
      renderChart()
      window.addEventListener('resize', () => chart && chart.resize())
    })

    watch(
      () => [props.nodes, props.edges, props.seedIds, props.activatedNodes],
      renderChart,
      { deep: true }
    )

    onBeforeUnmount(() => {
      window.removeEventListener('resize', () => chart && chart.resize())
      if (chart) { chart.dispose(); chart = null }
    })

    return { chartRef }
  }
}
</script>
