<template>
  <div id="app">
    <header class="app-header">
      <h1>KOL 传播仿真工具</h1>
      <p class="subtitle">基于 Independent Cascade 模型的社交网络传播模拟与 KOL 投放优化</p>
    </header>

    <div class="main-content">
      <!-- 控制面板 -->
      <aside class="control-panel">
        <section class="panel-section">
          <h3>网络生成</h3>
          <div class="form-group">
            <label>节点数</label>
            <input type="number" v-model.number="networkParams.node_count" min="50" max="2000" />
          </div>
          <div class="form-group">
            <label>KOL 数量</label>
            <input type="number" v-model.number="networkParams.kol_count" min="5" max="50" />
          </div>
          <div class="form-group">
            <label>连接数(m)</label>
            <input type="number" v-model.number="networkParams.m" min="1" max="10" />
          </div>
          <button class="btn btn-primary" @click="handleCreateNetwork" :disabled="loading">
            {{ loading ? '生成中...' : '生成网络' }}
          </button>
        </section>

        <section class="panel-section" v-if="kolIds.length">
          <h3>选择种子 KOL</h3>
          <div class="kol-list">
            <label v-for="id in kolIds" :key="id" class="kol-item"
              :class="{ selected: selectedSeeds.includes(id) }">
              <input type="checkbox" :value="id" v-model="selectedSeeds" />
              <span>KOL_{{ id }} (度: {{ getNodeDegree(id) }})</span>
            </label>
          </div>
        </section>

        <section class="panel-section" v-if="kolIds.length">
          <h3>仿真参数</h3>
          <div class="form-group">
            <label>传播概率</label>
            <input type="range" v-model.number="simParams.spread_prob" min="0.01" max="0.5" step="0.01" />
            <span>{{ simParams.spread_prob }}</span>
          </div>
          <div class="form-group">
            <label>传播步数</label>
            <input type="number" v-model.number="simParams.steps" min="1" max="30" />
          </div>
          <div class="form-group">
            <label>模拟次数</label>
            <input type="number" v-model.number="simParams.num_runs" min="10" max="500" />
          </div>
          <button class="btn btn-success" @click="handleSimulate" :disabled="!selectedSeeds.length || loading">
            运行仿真
          </button>
          <button class="btn btn-info" @click="handleSingleSim" :disabled="!selectedSeeds.length || loading">
            播放传播动画
          </button>
          <button class="btn btn-warning" @click="handleOptimize" :disabled="loading">
            智能推荐 Top-5
          </button>
        </section>

        <section class="panel-section" v-if="kolIds.length">
          <h3>对比组合</h3>
          <div class="form-group">
            <label>组合 A</label>
            <input type="text" v-model="comboAText" placeholder="如: 0,1,2" />
          </div>
          <div class="form-group">
            <label>组合 B</label>
            <input type="text" v-model="comboBText" placeholder="如: 3,4,5" />
          </div>
          <button class="btn btn-secondary" @click="handleCompare" :disabled="loading">
            对比传播效果
          </button>
        </section>
      </aside>

      <!-- 可视化区域 -->
      <main class="viz-area">
        <div class="tabs">
          <button :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">网络图</button>
          <button :class="{ active: activeTab === 'compare' }" @click="activeTab = 'compare'">传播对比</button>
          <button :class="{ active: activeTab === 'overlap' }" @click="activeTab = 'overlap'">重叠度矩阵</button>
          <button :class="{ active: activeTab === 'community' }" @click="activeTab = 'community'">社区分析</button>
        </div>

        <div class="tab-content">
          <div v-show="activeTab === 'graph'">
            <SpreadAnimation
              v-if="animationHistory.length"
              :history="animationHistory"
              @step-change="handleStepChange"
            />
            <NetworkGraph
              :nodes="graphNodes"
              :edges="graphEdges"
              :seed-ids="selectedSeeds"
              :activated-nodes="activatedNodes"
            />
            <div v-if="simResult" class="result-banner">
              平均传播覆盖: <strong>{{ simResult.avg_reach.toFixed(1) }}</strong> 人
              ({{ (simResult.avg_reach / networkParams.node_count * 100).toFixed(1) }}% 网络覆盖率)
            </div>
          </div>

          <div v-show="activeTab === 'compare'">
            <ComparisonChart :results="compareResults" />
            <div v-if="compareResults.length" class="compare-summary">
              <div v-for="(r, i) in compareResults" :key="i" class="compare-item">
                组合{{ i + 1 }} [{{ r.seed_ids.join(',') }}]: 覆盖 <strong>{{ r.avg_reach.toFixed(1) }}</strong> 人
              </div>
            </div>
          </div>

          <div v-show="activeTab === 'overlap'">
            <OverlapMatrix :kol-ids="kolIds" :matrix="overlapMatrix" />
            <p class="tip" v-if="overlapMatrix.length">颜色越深表示两个 KOL 的粉丝重叠度越高，选择重叠度低的组合可最大化覆盖。</p>
          </div>

          <div v-show="activeTab === 'community'">
            <CommunityAnalysis :communities="communities" />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import NetworkGraph from './components/NetworkGraph.vue'
import SpreadAnimation from './components/SpreadAnimation.vue'
import ComparisonChart from './components/ComparisonChart.vue'
import OverlapMatrix from './components/OverlapMatrix.vue'
import CommunityAnalysis from './components/CommunityAnalysis.vue'
import {
  createNetwork, getGraphLayout, runSimulation, runSingleSimulation,
  compareCombinations, getOverlap, optimizeSeeds, getCommunities
} from './api/index.js'

export default {
  name: 'App',
  components: { NetworkGraph, SpreadAnimation, ComparisonChart, OverlapMatrix, CommunityAnalysis },
  setup() {
    const loading = ref(false)
    const activeTab = ref('graph')
    const networkId = ref(null)
    const kolIds = ref([])
    const selectedSeeds = ref([])
    const graphNodes = ref([])
    const graphEdges = ref([])
    const activatedNodes = ref([])
    const animationHistory = ref([])
    const simResult = ref(null)
    const compareResults = ref([])
    const overlapMatrix = ref([])
    const communities = ref([])
    const comboAText = ref('')
    const comboBText = ref('')

    const networkParams = reactive({ node_count: 500, kol_count: 20, m: 3 })
    const simParams = reactive({ spread_prob: 0.1, steps: 10, num_runs: 100 })

    function getNodeDegree(id) {
      const node = graphNodes.value.find(n => n.id === id)
      return node ? node.degree : 0
    }

    async function handleCreateNetwork() {
      loading.value = true
      try {
        const res = await createNetwork(networkParams)
        networkId.value = res.data.network_id
        kolIds.value = res.data.kol_ids
        selectedSeeds.value = []
        activatedNodes.value = []
        animationHistory.value = []
        simResult.value = null
        compareResults.value = []

        const layoutRes = await getGraphLayout(networkId.value)
        graphNodes.value = layoutRes.data.nodes
        graphEdges.value = layoutRes.data.edges

        const overlapRes = await getOverlap(networkId.value)
        overlapMatrix.value = overlapRes.data.overlap_matrix

        const commRes = await getCommunities(networkId.value)
        communities.value = commRes.data.communities
      } finally {
        loading.value = false
      }
    }

    async function handleSimulate() {
      if (!selectedSeeds.value.length) return
      loading.value = true
      try {
        const res = await runSimulation(networkId.value, {
          seed_ids: selectedSeeds.value,
          ...simParams
        })
        simResult.value = res.data
        compareResults.value = [res.data]
      } finally {
        loading.value = false
      }
    }

    async function handleSingleSim() {
      if (!selectedSeeds.value.length) return
      loading.value = true
      try {
        const res = await runSingleSimulation(networkId.value, {
          seed_ids: selectedSeeds.value,
          ...simParams
        })
        animationHistory.value = res.data.history
        activatedNodes.value = [...selectedSeeds.value]
      } finally {
        loading.value = false
      }
    }

    function handleStepChange(activated) {
      activatedNodes.value = activated
    }

    async function handleCompare() {
      const parseCombo = (text) => text.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
      const comboA = parseCombo(comboAText.value)
      const comboB = parseCombo(comboBText.value)
      if (!comboA.length || !comboB.length) return

      loading.value = true
      try {
        const res = await compareCombinations(networkId.value, {
          combinations: [comboA, comboB],
          ...simParams
        })
        compareResults.value = res.data.results
        activeTab.value = 'compare'
      } finally {
        loading.value = false
      }
    }

    async function handleOptimize() {
      loading.value = true
      try {
        const res = await optimizeSeeds(networkId.value, {
          k: 5,
          spread_prob: simParams.spread_prob,
          steps: simParams.steps,
          num_runs: 50
        })
        selectedSeeds.value = res.data.selected_seeds
        simResult.value = { avg_reach: res.data.avg_reach, reach_curve: res.data.reach_curve }
        compareResults.value = [{ seed_ids: res.data.selected_seeds, avg_reach: res.data.avg_reach, reach_curve: res.data.reach_curve }]
      } finally {
        loading.value = false
      }
    }

    return {
      loading, activeTab, networkId, kolIds, selectedSeeds,
      graphNodes, graphEdges, activatedNodes, animationHistory,
      simResult, compareResults, overlapMatrix, communities,
      comboAText, comboBText, networkParams, simParams,
      getNodeDegree, handleCreateNetwork, handleSimulate,
      handleSingleSim, handleStepChange, handleCompare, handleOptimize
    }
  }
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; }

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white; padding: 20px 30px; text-align: center;
}
.app-header h1 { font-size: 24px; }
.subtitle { opacity: 0.85; margin-top: 5px; font-size: 14px; }

.main-content { display: flex; gap: 20px; padding: 20px; max-width: 1600px; margin: 0 auto; }

.control-panel {
  width: 300px; flex-shrink: 0;
  background: white; border-radius: 8px; padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1); height: fit-content;
  max-height: calc(100vh - 120px); overflow-y: auto;
}
.panel-section { margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
.panel-section:last-child { border-bottom: none; }
.panel-section h3 { font-size: 14px; color: #333; margin-bottom: 10px; }

.form-group { margin-bottom: 10px; }
.form-group label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }
.form-group input[type="number"],
.form-group input[type="text"] {
  width: 100%; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;
}
.form-group input[type="range"] { width: 80%; }
.form-group span { font-size: 12px; color: #666; }

.btn {
  display: block; width: 100%; padding: 8px; border: none; border-radius: 4px;
  font-size: 13px; cursor: pointer; margin-top: 8px; color: white; transition: opacity 0.2s;
}
.btn:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #667eea; }
.btn-success { background: #48bb78; }
.btn-info { background: #4299e1; }
.btn-warning { background: #ed8936; }
.btn-secondary { background: #718096; }

.kol-list { max-height: 200px; overflow-y: auto; }
.kol-item {
  display: flex; align-items: center; gap: 6px; padding: 4px 8px;
  border-radius: 4px; cursor: pointer; font-size: 12px; margin-bottom: 2px;
}
.kol-item:hover { background: #f0f4ff; }
.kol-item.selected { background: #ebf4ff; border: 1px solid #bee3f8; }
.kol-item input { margin: 0; }

.viz-area { flex: 1; min-width: 0; }

.tabs { display: flex; gap: 4px; margin-bottom: 15px; }
.tabs button {
  padding: 8px 16px; border: none; background: #e2e8f0;
  border-radius: 4px 4px 0 0; cursor: pointer; font-size: 13px;
}
.tabs button.active { background: white; font-weight: bold; box-shadow: 0 -2px 4px rgba(0,0,0,0.05); }

.tab-content {
  background: white; border-radius: 0 8px 8px 8px; padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-height: 600px;
}

.result-banner {
  margin-top: 15px; padding: 12px; background: #f0fff4;
  border: 1px solid #c6f6d5; border-radius: 4px; text-align: center; font-size: 14px;
}

.compare-summary { margin-top: 15px; }
.compare-item { padding: 8px 12px; background: #f7fafc; border-radius: 4px; margin-bottom: 6px; font-size: 13px; }

.tip { margin-top: 15px; font-size: 13px; color: #666; padding: 10px; background: #fffbeb; border-radius: 4px; }

.controls {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px; padding: 10px;
  background: #f7fafc; border-radius: 4px;
}
.controls button {
  padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px;
  background: white; cursor: pointer; font-size: 12px;
}
.controls button:hover { background: #edf2f7; }
.controls button:disabled { opacity: 0.5; }
.step-info, .reach-info { font-size: 12px; color: #4a5568; }

.community-list table { width: 100%; border-collapse: collapse; font-size: 13px; }
.community-list th, .community-list td { padding: 8px 12px; border: 1px solid #e2e8f0; text-align: center; }
.community-list th { background: #f7fafc; font-weight: 600; }
</style>
