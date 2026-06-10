<template>
  <div class="community-analysis">
    <div ref="chartRef" style="width: 100%; height: 350px;"></div>
    <div class="bottleneck-legend">
      <span class="legend-item"><span class="dot red"></span> 传播死胡同（跨圈连通率 &lt; 15%）</span>
      <span class="legend-item"><span class="dot yellow"></span> 传播受限（15%~30%）</span>
      <span class="legend-item"><span class="dot green"></span> 传播畅通（&gt; 30%）</span>
    </div>
    <div v-if="communities.length" class="community-table">
      <table>
        <thead>
          <tr>
            <th>社区</th><th>规模</th><th>跨圈连通率</th><th>桥接节点</th><th>诊断</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in enriched" :key="c.community_id" :class="c.levelClass">
            <td><span class="comm-badge" :style="{ background: getColor(c.community_id) }">社区 {{ c.community_id }}</span></td>
            <td>{{ c.size }} 人</td>
            <td>{{ (c.connectivity * 100).toFixed(1) }}%</td>
            <td>{{ c.bridge_count }} 个</td>
            <td class="diagnosis">{{ c.diagnosis }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'CommunityAnalysis',
  props: {
    communities: { type: Array, default: () => [] }
  },
  setup(props) {
    const chartRef = ref(null)
    let chart = null
    const colors = ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de','#3ba272','#fc8452','#9a60b4','#ea7ccc','#48b0d6']

    function getColor(id) {
      return colors[id % colors.length]
    }

    const enriched = computed(() => {
      return props.communities.map(c => {
        const totalEdges = c.internal_edges + c.external_edges
        const connectivity = totalEdges > 0 ? c.external_edges / totalEdges : 0
        let level, diagnosis, levelClass
        if (connectivity < 0.15) {
          level = 'dead'
          diagnosis = '🚫 死胡同：信息进来出不去，必须在此社区内埋种子'
          levelClass = 'row-dead'
        } else if (connectivity < 0.30) {
          level = 'limited'
          diagnosis = '⚠️ 受限：跨圈传播弱，建议布置桥接型KOL'
          levelClass = 'row-limited'
        } else {
          level = 'open'
          diagnosis = '✅ 畅通：信息可自然扩散到其他圈层'
          levelClass = 'row-open'
        }
        return { ...c, connectivity, level, diagnosis, levelClass }
      })
    })

    function renderChart() {
      if (!chart || !props.communities.length) return

      const data = enriched.value.map(c => {
        const totalEdges = c.internal_edges + c.external_edges
        return {
          name: `社区${c.community_id} (${c.size}人)`,
          internal: c.internal_edges,
          external: c.external_edges,
          connectivity: c.connectivity,
        }
      })

      const option = {
        title: { text: '社区跨圈连通性分析', left: 'center', textStyle: { fontSize: 14 } },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params) => {
            const d = data[params[0].dataIndex]
            return `<b>${d.name}</b><br/>内部边: ${d.internal}<br/>跨圈边: ${d.external}<br/>连通率: ${(d.connectivity*100).toFixed(1)}%`
          }
        },
        grid: { left: 120, right: 40, top: 50, bottom: 30 },
        xAxis: { type: 'value', name: '边数' },
        yAxis: {
          type: 'category',
          data: data.map(d => d.name),
          axisLabel: { fontSize: 11 }
        },
        series: [
          {
            name: '内部边',
            type: 'bar',
            stack: 'total',
            data: data.map(d => d.internal),
            itemStyle: { color: '#a0aec0' },
            barMaxWidth: 20,
          },
          {
            name: '跨圈边',
            type: 'bar',
            stack: 'total',
            data: data.map((d, i) => ({
              value: d.external,
              itemStyle: {
                color: d.connectivity < 0.15 ? '#fc8181'
                  : d.connectivity < 0.30 ? '#f6e05e'
                  : '#68d391'
              }
            })),
            barMaxWidth: 20,
          }
        ]
      }

      chart.setOption(option, true)
    }

    onMounted(() => {
      chart = echarts.init(chartRef.value)
      renderChart()
      window.addEventListener('resize', () => chart && chart.resize())
    })

    watch(() => props.communities, renderChart, { deep: true })

    onBeforeUnmount(() => {
      if (chart) { chart.dispose(); chart = null }
    })

    return { chartRef, enriched, getColor }
  }
}
</script>

<style scoped>
.bottleneck-legend {
  display: flex; gap: 16px; justify-content: center; margin: 12px 0;
  font-size: 12px; color: #4a5568;
}
.legend-item { display: flex; align-items: center; gap: 4px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.red { background: #fc8181; }
.dot.yellow { background: #f6e05e; }
.dot.green { background: #68d391; }

.community-table { margin-top: 16px; }
.community-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
.community-table th { background: #2d3748; color: white; padding: 8px 10px; text-align: left; }
.community-table td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }
.comm-badge { padding: 2px 8px; border-radius: 10px; color: white; font-size: 11px; }
.diagnosis { font-size: 11px; }

.row-dead { background: #fff5f5; }
.row-limited { background: #fffff0; }
.row-open { background: #f0fff4; }
</style>
