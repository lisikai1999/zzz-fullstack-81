<template>
  <div class="spread-animation" v-if="history.length">
    <div class="anim-controls">
      <button class="anim-btn play" @click="startAnimation" :disabled="playing">▶ 播放</button>
      <button class="anim-btn" @click="stepForward" :disabled="playing || currentStep >= totalSteps">⏭ 下一步</button>
      <button class="anim-btn" @click="stopAnimation" :disabled="!playing">⏸ 暂停</button>
      <button class="anim-btn" @click="resetAnimation">↺ 重置</button>
      <input type="range" :min="0" :max="totalSteps" v-model.number="currentStep" @input="onSliderChange" class="step-slider" />
      <div class="anim-stats">
        <span class="badge step-badge">步骤 {{ currentStep }}/{{ totalSteps }}</span>
        <span class="badge reach-badge">覆盖 {{ activatedCount }} 人</span>
        <span class="badge new-badge" v-if="currentStep > 0">本步新增 +{{ currentStepNew }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'SpreadAnimation',
  props: {
    history: { type: Array, default: () => [] },
  },
  emits: ['step-change'],
  setup(props, { emit }) {
    const currentStep = ref(0)
    const playing = ref(false)
    let timer = null

    const totalSteps = computed(() => Math.max(0, props.history.length - 1))

    const activatedCount = computed(() => {
      let count = 0
      for (let i = 0; i <= currentStep.value; i++) {
        count += (props.history[i] || []).length
      }
      return count
    })

    const currentStepNew = computed(() => {
      return (props.history[currentStep.value] || []).length
    })

    function emitCurrentActivated() {
      const activated = []
      for (let i = 0; i <= currentStep.value; i++) {
        activated.push(...(props.history[i] || []))
      }
      emit('step-change', activated)
    }

    function startAnimation() {
      if (!props.history.length) return
      if (currentStep.value >= totalSteps.value) {
        currentStep.value = 0
      }
      playing.value = true
      timer = setInterval(() => {
        if (currentStep.value >= totalSteps.value) {
          stopAnimation()
          return
        }
        currentStep.value++
        emitCurrentActivated()
      }, 1000)
    }

    function stepForward() {
      if (currentStep.value < totalSteps.value) {
        currentStep.value++
        emitCurrentActivated()
      }
    }

    function stopAnimation() {
      playing.value = false
      if (timer) { clearInterval(timer); timer = null }
    }

    function resetAnimation() {
      stopAnimation()
      currentStep.value = 0
      emitCurrentActivated()
    }

    function onSliderChange() {
      emitCurrentActivated()
    }

    watch(() => props.history, () => {
      currentStep.value = 0
      emitCurrentActivated()
    })

    return { currentStep, totalSteps, activatedCount, currentStepNew, playing, startAnimation, stepForward, stopAnimation, resetAnimation, onSliderChange }
  }
}
</script>

<style scoped>
.anim-controls {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 12px 16px; background: linear-gradient(to right, #1a202c, #2d3748);
  border-radius: 8px; margin-bottom: 12px;
}
.anim-btn {
  padding: 6px 14px; border: none; border-radius: 4px;
  background: #4a5568; color: #fff; cursor: pointer; font-size: 12px;
  transition: background 0.2s;
}
.anim-btn:hover:not(:disabled) { background: #718096; }
.anim-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.anim-btn.play { background: #48bb78; }
.anim-btn.play:hover:not(:disabled) { background: #38a169; }
.step-slider { flex: 1; min-width: 100px; cursor: pointer; }
.anim-stats { display: flex; gap: 8px; margin-left: auto; }
.badge {
  padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
}
.step-badge { background: #4299e1; color: white; }
.reach-badge { background: #ed8936; color: white; }
.new-badge { background: #48bb78; color: white; }
</style>
