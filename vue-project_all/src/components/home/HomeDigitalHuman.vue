<template>
  <Teleport to="body">
  <div class="human-assistant" @keydown.esc="close">
    <Transition name="human-popup">
      <section v-if="open" id="digital-human-panel" class="human-panel" aria-label="数字人讲解窗口">
        <div class="human-dialogue">
          <header><h2>平台数字人</h2><button ref="closeButton" type="button" aria-label="关闭数字人弹窗" @click="close">×</button></header>
          <div class="human-conversation" aria-live="polite">
            <p class="human-bubble">大家好，我是平台的数字讲解员，带您了解交通事故智能决策与救援推演系统。</p>
            <p class="human-bubble">系统面向“两客一危”事故应急救援，旨在打通现场感知、事故研判与救援调度，提高事故发现、科学决策和多部门协同处置能力。</p>
            <p class="human-bubble">我们以湖北仙桃货车追尾客车、团风甲醇槽罐车侧翻泄漏两起事故为背景，开展数字孪生实验。</p>
          </div>
        </div>
      </section>
    </Transition>
    <button ref="launcher" class="human-launcher" :class="{ 'human-launcher--fallback': imageUnavailable }" type="button" :aria-expanded="open" aria-controls="digital-human-panel" aria-label="打开或收起数字人讲解窗口" @click="toggle">
      <span v-if="imageUnavailable">数字人讲解</span>
      <img v-else :src="assistantImageUrl" alt="数字人助手" draggable="false" @error="imageUnavailable = true" />
    </button>
  </div>
  </Teleport>
</template>

<script setup>
import { nextTick, ref } from 'vue'

const props = defineProps({
  accidentTitle: { type: String, default: '客车追尾现场' },
  phase: { type: Object, default: null },
})
const assistantImageUrl = `${import.meta.env.BASE_URL}hud-assets/digital-human-assistant.gif`
const imageUnavailable = ref(false)
const open = ref(false)
const launcher = ref(null)
const closeButton = ref(null)
async function toggle() {
  open.value = !open.value
  if (open.value) { await nextTick(); closeButton.value?.focus() }
}
async function close() { open.value = false; await nextTick(); launcher.value?.focus() }
</script>

<style scoped>
@font-face {
  font-family: 'LkywOppoSans';
  src: url('/hud-assets/fonts/oppo-sans-regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
.human-bubble { font-family: 'LkywOppoSans', 'Microsoft YaHei', sans-serif; font-weight: 400; font-style: normal; }

@font-face {
  font-family: 'LkywTencentSans';
  src: url('/hud-assets/fonts/tencent-sans-w7.otf') format('opentype');
  font-display: swap;
}

.human-assistant { user-select: none; caret-color: transparent; position: fixed; right: calc(clamp(360px, 22vw, 440px) + 32px); bottom: 240px; z-index: 30; width: 210px; color: #e6f5ff; font-family: 'LkywTencentSans', 'Microsoft YaHei', sans-serif; }
button { font: inherit; color: inherit; cursor: pointer; }
button:focus-visible { outline: 2px solid #7beaff; outline-offset: 4px; }
.human-launcher { overflow: hidden; clip-path: inset(0 15%); isolation: isolate; appearance: none; box-shadow: none; outline: none; position: relative; z-index: 2; display: block; width: 100%; padding: 0; border: 0; background: none; }
.human-launcher--fallback { clip-path: none; width: auto; margin-left: auto; padding: 10px 16px; border: 1px solid #53deef; border-radius: 7px; background: #103761; }
.human-launcher:focus-visible:not(.human-launcher--fallback) { outline: none; }
.human-launcher:focus-visible img { filter: none; outline: 2px solid #53deef; outline-offset: 2px; }
.human-launcher img {  display: block; width: 100%; height: 360px; object-fit: contain; filter: none; }
.human-launcher:hover img { filter: none; }
.human-panel { position: fixed; right: 0; top: 160px; bottom: 35px; width: min(360px, calc(100vw - 180px)); display: flex; border: 2px solid #77c9e2a6; background: #102d54; box-shadow: 0 12px 45px #0008; overflow: hidden; }
.human-dialogue { width: 100%; display: flex; flex-direction: column; min-width: 0; min-height: 0; background: linear-gradient(180deg, #8b9bb6, #18345b); }
header { display: flex; align-items: center; justify-content: space-between; min-height: 75px; padding: 0 22px; background: #0a254a; border-bottom: 1px solid #88d5ed66; }
h2 { margin: 0; font-size: 24px; letter-spacing: 2px; }
header button { border: 0; background: transparent; padding: 8px; font-size: 28px; }
.human-conversation { flex: 1; min-height: 0; overflow-y: auto; padding: 24px 20px; }
.human-bubble { margin: 0 0 22px; padding: 20px; border-radius: 12px; background: #103761; color: #edf8ff; font-size: 19px; line-height: 1.95; box-shadow: inset 0 1px 0 #8dd4ef22; overflow-wrap: anywhere; }
.human-phase { margin-bottom: 12px; color: #f0f8ff; font-size: 13px; line-height: 1.7; }
footer { margin: 14px 20px 20px; padding: 16px 12px; border: 1px solid #5f91be44; border-radius: 7px; background: #081d3d; color: #b5cbe0; font-size: 13px; text-align: center; }
.human-popup-enter-active, .human-popup-leave-active { transition: opacity .22s, transform .22s; }
.human-popup-enter-from, .human-popup-leave-to { opacity: 0; transform: translateX(20px); }
@media (max-width: 1250px) { .human-assistant { right: 362px; } }
@media (max-width: 1050px) { .human-assistant { right: 332px; } }
@media (max-width: 1100px) { .human-panel { right: 0; top: 155px; bottom: 30px; } }
@media (max-width: 720px) { .human-panel { right: 0; top: 155px; bottom: 210px; width: calc(100vw - 24px); } header { padding: 0 12px; min-height: 50px; } h2 { font-size: 18px; } .human-conversation { padding: 12px; } .human-bubble { padding: 12px; font-size: 14px; } footer { margin: 10px; padding: 10px; } }
@media (prefers-reduced-motion: reduce) { .human-popup-enter-active, .human-popup-leave-active { transition: none; } }
</style>
