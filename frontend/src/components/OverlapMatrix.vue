<template>
  <div class="overlap-matrix">
    <div ref="chartRef" style="width: 100%; height: 500px;"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'OverlapMatrix',
  props: {
    kolIds: { type: Array, default: () => [] },
    matrix: { type: Array, default: () => [] }
  },
  setup(props) {
    const chartRef = ref(null)
    let chart = null

    function renderChart() {
      if (!chart || !props.matrix.length) return

      const labels = props.kolIds.map(id => `KOL_${id}`)
      const data = []
      for (let i = 0; i < props.matrix.length; i++) {
        for (let j = 0; j < props.matrix[i].length; j++) {
          data.push([j, i, +(props.matrix[i][j]).toFixed(3)])
        }
      }

      const option = {
        title: { text: 'KOL 粉丝重叠度矩阵 (Jaccard)', left: 'center' },
        tooltip: {
          formatter: (params) => `${labels[params.value[1]]} ↔ ${labels[params.value[0]]}<br/>重叠度: ${params.value[2]}`
        },
        grid: { top: 60, bottom: 80, left: 80, right: 40 },
        xAxis: { type: 'category', data: labels, axisLabel: { rotate: 45 } },
        yAxis: { type: 'category', data: labels },
        visualMap: {
          min: 0, max: 1, calculable: true,
          orient: 'horizontal', left: 'center', bottom: 10,
          inRange: { color: ['#f7fbff', '#08306b'] }
        },
        series: [{
          type: 'heatmap',
          data,
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } }
        }]
      }

      chart.setOption(option, true)
    }

    onMounted(() => {
      chart = echarts.init(chartRef.value)
      renderChart()
      window.addEventListener('resize', () => chart && chart.resize())
    })

    watch(() => [props.kolIds, props.matrix], renderChart, { deep: true })

    onBeforeUnmount(() => {
      if (chart) { chart.dispose(); chart = null }
    })

    return { chartRef }
  }
}
</script>
