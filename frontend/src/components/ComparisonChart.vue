<template>
  <div class="comparison-chart">
    <div ref="chartRef" style="width: 100%; height: 400px;"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'ComparisonChart',
  props: {
    results: { type: Array, default: () => [] }
  },
  setup(props) {
    const chartRef = ref(null)
    let chart = null

    function renderChart() {
      if (!chart || !props.results.length) return

      const series = props.results.map((result, idx) => ({
        name: `组合${idx + 1}: [${result.seed_ids.join(',')}]`,
        type: 'line',
        smooth: true,
        data: result.reach_curve,
        emphasis: { focus: 'series' },
      }))

      const xData = props.results[0].reach_curve.map((_, i) => `步骤${i}`)

      const option = {
        title: { text: '传播范围对比', left: 'center' },
        tooltip: { trigger: 'axis' },
        legend: { top: 30 },
        grid: { top: 80, bottom: 40 },
        xAxis: { type: 'category', data: xData, name: '传播步骤' },
        yAxis: { type: 'value', name: '覆盖人数' },
        series
      }

      chart.setOption(option, true)
    }

    onMounted(() => {
      chart = echarts.init(chartRef.value)
      renderChart()
      window.addEventListener('resize', () => chart && chart.resize())
    })

    watch(() => props.results, renderChart, { deep: true })

    onBeforeUnmount(() => {
      if (chart) { chart.dispose(); chart = null }
    })

    return { chartRef }
  }
}
</script>
