<template>
  <header class="system-chrome">
    <div class="system-chrome__title-assembly">
      <img class="system-chrome__line system-chrome__line--left" src="/hud-assets/top-line-left.svg" alt="" />
      <button class="system-chrome__brand" type="button" @click="navigate('/')" aria-label="返回系统首页">
        <img src="/hud-assets/title-banner-decoration.svg" alt="" />
        <span>基于数字孪生的交通事故智能决策与救援推演平台</span>
      </button>
      <img class="system-chrome__line system-chrome__line--right" src="/hud-assets/top-line-right.svg" alt="" />
    </div>

    <div class="system-chrome__weather-tools">
      <section class="system-chrome__weather" aria-label="系统时间">
        <span class="weather-icon">{{ activeWeather.icon }}</span>
        <span>{{ dateText }}</span>
        <i></i>
        <strong>{{ timeText }}</strong>
      </section>

      <button
        type="button"
        class="weather-control-button"
        :class="{ active: showWeatherControl }"
        :aria-expanded="showWeatherControl"
        aria-controls="weather-control-panel"
        @click="showWeatherControl = !showWeatherControl"
      >
        <span class="weather-control-button__icon">{{ activeWeather.icon }}</span>
        <span><small>场景天气</small><b>{{ activeWeather.label }}</b></span>
        <span class="weather-control-button__chevron">⌄</span>
      </button>

      <aside v-if="showWeatherControl" id="weather-control-panel" class="weather-control-panel" aria-label="场景天气调节">
        <div class="weather-control-panel__head">
          <div><span>环境渲染</span><strong>天气与亮度</strong></div>
          <button type="button" aria-label="关闭天气调节" @click="showWeatherControl = false">×</button>
        </div>
        <div class="weather-preset-grid">
          <button
            v-for="weather in weatherPresets"
            :key="weather.key"
            type="button"
            :class="{ selected: selectedWeather === weather.key }"
            @click="selectWeather(weather)"
          >
            <span>{{ weather.icon }}</span><b>{{ weather.label }}</b><small>{{ weather.desc }}</small>
          </button>
        </div>
        <label class="weather-brightness-control">
          <span><b>地图明亮度</b><output>{{ sceneBrightness }}%</output></span>
          <input v-model.number="sceneBrightness" type="range" min="95" max="145" step="1" aria-label="地图明亮度" />
        </label>
        <p>已同步至三维场景；设置将保存在本浏览器。</p>
      </aside>
    </div>

    <nav class="system-chrome__nav" aria-label="系统导航">
      <button
        v-for="item in visibleNavigation"
        :key="item.path"
        type="button"
        :class="{ active: isActive(item.path) }"
        @click="navigate(item.path)"
      >
        <img :src="isActive(item.path) ? '/hud-assets/nav-active.png' : '/hud-assets/nav-default.png'" alt="" />
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="system-chrome__actions">
      <div class="role-select">
        <span>当前岗位</span>
        <span>{{ currentRoleProfile.label }}</span>
        <button class="logout-button" type="button" @click="logout"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 4H5v16h5M14 8l4 4-4 4M9 12h10" /></svg><span>退出登录</span></button>
      </div>
    </div>

  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { canAccessRoute, currentRoleProfile } from '../composables/useRoleAccess'

import { signOut } from '../composables/useAuth'
async function logout() {
  try { await signOut(); await router.replace('/login') }
  catch { window.alert('退出失败，请稍后重试') }
}
const route = useRoute()
const router = useRouter()
const now = ref(new Date())
const showWeatherControl = ref(false)
let timer

const WEATHER_STORAGE_KEY = 'lkyw.systemChrome.weatherVisual'
const weatherPresets = Object.freeze([
  { key: 'clear', icon: '☀', label: '晴朗明亮', desc: '推荐', brightness: 128, saturation: 1.12, contrast: 1.04 },
  { key: 'cloudy', icon: '⛅', label: '多云', desc: '柔和', brightness: 116, saturation: 0.94, contrast: 1 },
  { key: 'rain', icon: '🌧', label: '雨雾', desc: '低能见度', brightness: 106, saturation: 0.78, contrast: 0.94 },
  { key: 'night', icon: '☾', label: '夜间', desc: '夜景值守', brightness: 96, saturation: 0.76, contrast: 1.02 },
])
const selectedWeather = ref('clear')
const sceneBrightness = ref(128)
const activeWeather = computed(() => weatherPresets.find((weather) => weather.key === selectedWeather.value) || weatherPresets[0])
const navigation = [
  { label: '综合态势', path: '/' },
  { label: '感知组网', path: '/sensor-manage' },
  { label: '实时检测', path: '/realtime' },
  { label: '协同响应', path: '/coordination' },
  { label: '精细建模', path: '/modeling' },
  { label: '仿真推演', path: '/simulation' },
]
const visibleNavigation = computed(() =>
  navigation.filter(({ path }) => canAccessRoute(router.resolve(path).meta.roles)),
)

const dateText = computed(() => now.value.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }))
const timeText = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))
const isActive = (path) => path === '/' ? route.path === '/' && route.query.view === 'overview' : route.path.startsWith(path)
const navigate = (path) => {
  if (path === '/') {
    // 再次点击已点亮的综合态势，返回无选中导航的迎宾视角。
    return router.push(isActive('/') ? { path: '/' } : { path: '/', query: { view: 'overview' } })
  }
  return router.push(path)
}
const applyWeatherVisual = () => {
  const weather = activeWeather.value
  const root = document.documentElement
  root.dataset.weatherMode = weather.key
  root.style.setProperty('--scene-brightness', String(sceneBrightness.value / 100))
  root.style.setProperty('--scene-saturation', String(weather.saturation))
  root.style.setProperty('--scene-contrast', String(weather.contrast))
}
const selectWeather = (weather) => {
  selectedWeather.value = weather.key
  sceneBrightness.value = weather.brightness
}
onMounted(() => {
  timer = window.setInterval(() => { now.value = new Date() }, 1000)
  try {
    const saved = JSON.parse(window.localStorage.getItem(WEATHER_STORAGE_KEY) || '{}')
    if (weatherPresets.some((weather) => weather.key === saved.mode)) selectedWeather.value = saved.mode
    if (Number.isFinite(Number(saved.brightness))) sceneBrightness.value = Math.min(145, Math.max(95, Number(saved.brightness)))
  } catch { /* 使用推荐的晴朗明亮模式。 */ }
  applyWeatherVisual()
})
onBeforeUnmount(() => window.clearInterval(timer))
watch([selectedWeather, sceneBrightness], () => {
  applyWeatherVisual()
  try {
    window.localStorage.setItem(WEATHER_STORAGE_KEY, JSON.stringify({ mode: selectedWeather.value, brightness: sceneBrightness.value }))
  } catch { /* 忽略存储失败。 */ }
})
</script>

<style scoped>
@font-face {
  font-family: 'LkywTencentSans';
  src: url('/hud-assets/fonts/tencent-sans-w7.otf') format('opentype');
  font-display: swap;
}
.system-chrome { position: relative; z-index: 1000; height: 96px; flex: 0 0 96px; color: #b8e7ff; background: linear-gradient(180deg, rgba(3, 19, 37, .98), rgba(3, 17, 33, .78)); border-bottom: 1px solid rgba(58, 159, 212, .35); box-shadow: 0 5px 22px rgba(0, 0, 0, .36); user-select: none; }
.system-chrome__title-assembly { position: absolute; z-index: 2; top: 13px; left: 50%; display: flex; align-items: flex-start; height: 74px; transform: translateX(-50%); white-space: nowrap; }
.system-chrome__line { position: relative; z-index: 0; flex: 0 0 562px; width: 562px; height: 43px; margin-top: 1px; opacity: .95; pointer-events: none; transform-origin: center center; }.system-chrome__line--left { margin-right: -4px; transform: translate(-131px, 0) scale(1); }.system-chrome__line--right { margin-left: -4px; transform: translate(131px, 2px) scale(1); }
.system-chrome__weather-tools { position: absolute; z-index: 8; top: 18px; left: 28px; display: flex; align-items: center; gap: 14px; }.system-chrome__weather { display: flex; align-items: center; gap: 11px; font-size: 16px; color: #b8eaff; }.weather-icon { width: 28px; color: #ffe681; font-size: 27px; text-align: center; filter: drop-shadow(0 0 7px rgba(255, 218, 86, .62)); }.system-chrome__weather i { height: 28px; width: 1px; background: #3f7899; }.system-chrome__weather strong { letter-spacing: 1.5px; color: #effbff; font-size: 17px; }
.weather-control-button { display: flex; align-items: center; gap: 7px; min-width: 126px; padding: 5px 9px 5px 7px; border: 1px solid rgba(88, 209, 255, .65); border-radius: 5px; background: linear-gradient(135deg, rgba(10, 91, 139, .78), rgba(7, 36, 73, .86)); box-shadow: inset 0 0 12px rgba(55, 205, 255, .12), 0 0 12px rgba(34, 180, 242, .14); color: #e8fbff; cursor: pointer; font-family: inherit; text-align: left; transition: .2s ease; }.weather-control-button:hover, .weather-control-button.active { border-color: #ffe582; background: linear-gradient(135deg, rgba(126, 103, 23, .83), rgba(49, 54, 37, .92)); box-shadow: inset 0 0 15px rgba(255, 222, 110, .16), 0 0 16px rgba(255, 213, 76, .34); }.weather-control-button__icon { color: #ffe681; font-size: 24px; line-height: 1; filter: drop-shadow(0 0 6px rgba(255, 218, 86, .7)); }.weather-control-button small, .weather-control-button b { display: block; white-space: nowrap; }.weather-control-button small { color: #9ddcf0; font-size: 10px; line-height: 1.1; }.weather-control-button b { margin-top: 2px; color: #f4fcff; font-size: 12px; letter-spacing: .4px; }.weather-control-button__chevron { margin-left: auto; color: #91e4ff; font-size: 17px; line-height: 1; }.weather-control-panel { position: absolute; top: 49px; left: 244px; width: 304px; padding: 12px; border: 1px solid rgba(85, 218, 255, .72); border-radius: 7px; background: linear-gradient(145deg, rgba(5, 35, 62, .98), rgba(8, 71, 105, .96)); box-shadow: 0 14px 32px rgba(0, 0, 0, .48), inset 0 0 20px rgba(55, 208, 255, .12); color: #dff8ff; }.weather-control-panel__head { display: flex; align-items: center; justify-content: space-between; padding-bottom: 9px; border-bottom: 1px solid rgba(105, 222, 255, .26); }.weather-control-panel__head span, .weather-control-panel__head strong { display: block; }.weather-control-panel__head span { color: #8dd9f1; font-size: 10px; letter-spacing: 1px; }.weather-control-panel__head strong { margin-top: 2px; color: #fff4bd; font-size: 15px; }.weather-control-panel__head button { border: 0; background: transparent; color: #b5edff; font-size: 22px; cursor: pointer; }.weather-preset-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin-top: 10px; }.weather-preset-grid button { display: grid; grid-template-columns: 28px 1fr; grid-template-rows: 17px 14px; align-items: center; padding: 7px; border: 1px solid rgba(101, 199, 231, .25); border-radius: 4px; background: rgba(2, 25, 49, .52); color: #cdeeff; cursor: pointer; text-align: left; transition: .18s ease; }.weather-preset-grid button:hover, .weather-preset-grid button.selected { border-color: #ffe37b; background: linear-gradient(135deg, rgba(132, 105, 25, .43), rgba(17, 75, 100, .62)); box-shadow: inset 0 0 12px rgba(255, 220, 102, .1); }.weather-preset-grid button > span { grid-row: 1 / span 2; color: #ffe681; font-size: 21px; }.weather-preset-grid b { font-size: 12px; }.weather-preset-grid small { color: #90cfe4; font-size: 10px; }.weather-brightness-control { display: block; margin-top: 12px; padding: 9px; border: 1px solid rgba(93, 201, 237, .22); background: rgba(0, 20, 43, .37); }.weather-brightness-control > span { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }.weather-brightness-control output { color: #ffe680; font-family: Consolas, monospace; }.weather-brightness-control input { width: 100%; margin: 8px 0 0; accent-color: #ffe16b; cursor: ew-resize; }.weather-control-panel p { margin: 8px 0 0; color: #8bc8df; font-size: 10px; line-height: 1.4; }
.system-chrome__brand { position: relative; z-index: 2; flex: 0 0 530px; width: 530px; height: 63px; transform: none; border: 0; background: none; color: #ecfaff; cursor: pointer; }.system-chrome__brand img { position: absolute; z-index: 0; top: 4px; left: -60px; width: 650px; height: 77px; transform: translate(-4px, -2px) scale(1.27); transform-origin: center center; }.system-chrome__brand span { position: relative; z-index: 1; display: block; padding: 11px 0 0; overflow: visible; white-space: nowrap; font-size: clamp(23px, 1.32vw, 26px); line-height: 1.15; font-weight: 900; font-style: italic; letter-spacing: 1.7px; transform: translate(-56px, 2px) scale(1.1); transform-origin: center center; text-shadow: 0 0 3px rgba(220, 249, 255, .9), 0 0 10px rgba(73, 194, 255, .82), 0 0 20px rgba(15, 128, 215, .4); }
.system-chrome__nav { position: absolute; z-index: 4; top: calc(100% + 22px); left: 50%; transform: translateX(-50%); display: flex; gap: clamp(10px, 1.35vw, 30px); }.system-chrome__nav button { position: relative; display: flex; align-items: center; justify-content: center; text-align: center; line-height: 1; width: clamp(140px, 10.6vw, 190px); height: 42px; flex-shrink: 0; padding: 0; border: 0; background: linear-gradient(90deg, rgba(35,116,177,.7), rgba(7,49,87,.72)); clip-path: polygon(10% 0,90% 0,100% 50%,90% 100%,10% 100%,0 50%); color: #ddf6ff; cursor: pointer; font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-size: clamp(19px, 1.3vw, 24px); font-weight: 600; letter-spacing: .55px; }.system-chrome__nav button.active { color: #fff7bf; background: linear-gradient(90deg, rgba(153,125,25,.8), rgba(74,64,19,.9)); }.system-chrome__nav button img { position: absolute; inset: 0; width: 100%; height: 100%; }.system-chrome__nav button span { position: relative; display: block; line-height: 1; white-space: nowrap; transform: translateY(-2px); }
.system-chrome__actions { position: absolute; right: 28px; top: 25px; display: flex; align-items: center; }.role-select { display: flex; align-items: center; gap: 8px; color: #8fd5ef; font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-size: 18px; }.role-select select { max-width: 120px; min-height: 30px; padding: 2px 6px; border: 1px solid rgba(92, 194, 241, .38); background: #08223b; color: #e5f8ff; border-radius: 3px; font-family: inherit; font-size: 18px; }.system-chrome__nav button:hover { filter: brightness(1.22); }
@media (max-width: 1050px) { .system-chrome { height: 74px; flex-basis: 74px; }.system-chrome__title-assembly { transform: translateX(-50%) scale(.68); transform-origin: top center; }.system-chrome__brand span { padding-top: 4px; font-size: 21px; }.system-chrome__actions { right: 12px; top: 16px; }.role-select { display: none; }.system-chrome__weather-tools { top: 16px; left: 14px; gap: 8px; }.system-chrome__weather { font-size: 13px; }.weather-icon { font-size: 24px; }.system-chrome__weather strong { font-size: 14px; }.weather-control-button { min-width: 108px; padding: 4px 6px; }.weather-control-button small { display: none; }.weather-control-panel { top: 43px; left: 188px; }.system-chrome__nav { top: calc(100% + 19px); gap: 7px; }.system-chrome__nav button { width: 112px; height: 34px; font-size: 15px; } }
@media (max-width: 720px) { .system-chrome { height: 62px; flex-basis: 62px; }.system-chrome__title-assembly { top: 2px; width: 100%; height: 43px; transform: none; left: 0; display: block; }.system-chrome__brand { position: absolute; left: 50%; width: calc(100vw - 12px); height: 43px; transform: translateX(-50%); }.system-chrome__brand img { width: 100%; height: 100%; }.system-chrome__brand span { padding: 4px 6px 0; overflow: visible; text-overflow: clip; font-size: clamp(12px, 3vw, 17px); letter-spacing: 1px; }.system-chrome__weather-tools, .system-chrome__actions { display: none; }.system-chrome__nav { top: calc(100% + 18px); width: 100%; justify-content: center; overflow: hidden; }.system-chrome__nav button { width: 62px; height: 28px; flex: 0 0 62px; font-size: 11px; }.system-chrome__line { display: none; } }
</style>

<style scoped>
.role-select { font-family: 'LkywTencentSans', 'Microsoft YaHei', sans-serif; font-weight: 600; gap: 10px; }
.role-select > span:nth-child(2) { color: #dff6ff; }
.logout-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 34px; margin-left: 7px; padding: 5px 12px; border: 1px solid #64c5e477; border-radius: 4px; background: linear-gradient(135deg,#16415c,#0a263e); box-shadow: inset 0 1px #c0f1ff15; color: #bfeafa; font-family: inherit; font-size: 15px; cursor: pointer; transition: background .18s, border-color .18s, color .18s; }
.logout-button svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.logout-button:hover { background: #17516c; border-color: #83e1f3; color: #fff; }
.logout-button:focus-visible { outline: 2px solid #83e1f3; outline-offset: 3px; }
.logout-button:active { transform: translateY(1px); }
</style>
