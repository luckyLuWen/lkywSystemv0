<template>
  <div class="login-screen">
    <header class="platform-heading"><i></i><span>基于数字孪生的交通事故智能决策与救援推演平台</span><small>DIGITAL TWIN · EMERGENCY COMMAND</small></header>
    <div class="login-brand"><div class="brand-kicker">两客一危 · 应急救援</div><h1>感知全域态势<br><em>协同每一次救援</em></h1><p>让现场信息连接科学决策，让救援力量高效协同。</p>
      <div class="network-art" aria-hidden="true">
        <div class="flow-step"><span class="flow-number">01</span><i></i><strong>现场感知</strong><small>多源数据汇聚</small></div>
        <div class="flow-connector"><span>→</span></div>
        <div class="flow-step flow-step--center"><span class="flow-number">02</span><i></i><strong>事故研判</strong><small>智能分析决策</small></div>
        <div class="flow-connector"><span>→</span></div>
        <div class="flow-step"><span class="flow-number">03</span><i></i><strong>救援调度</strong><small>多方协同处置</small></div>
      </div>
      <div class="capabilities"><span>01 <b>全域感知</b></span><span>02 <b>智能研判</b></span><span>03 <b>协同处置</b></span></div>
    </div>
    <form class="login-card" @submit.prevent="submit">
      <small>SECURE ACCESS</small><h2>欢迎进入指挥平台</h2><p class="hint">请选择岗位，并使用对应账号登录系统</p>
      <fieldset><legend>选择岗位</legend><div class="roles"><button v-for="item in ROLE_OPTIONS" :key="item.key" type="button" :class="{selected: role === item.key}" :aria-pressed="role === item.key" @click="role = item.key"><span class="role-icon">{{ item.icon }}</span>{{ item.label }}<span class="role-check" v-if="role === item.key">✓</span></button></div></fieldset>
      <label>账号<input v-model.trim="username" name="username" autocomplete="username" required maxlength="128" placeholder="请输入账号" /></label>
      <label>密码<input v-model="password" name="password" type="password" autocomplete="current-password" required maxlength="256" placeholder="请输入密码" /></label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="submit" :disabled="busy">{{ busy ? '正在验证…' : '登录系统' }}</button>
      <p class="hint note">账号由系统管理员分配，岗位须与账号权限一致</p>
    </form>
    <div class="page-footer">交通应急救援 · 数字孪生实验平台 <span>安全接入 / 身份验证</span></div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ROLE_OPTIONS } from '../composables/useRoleAccess'
import { signIn } from '../composables/useAuth'
const router = useRouter()
const role = ref('commander'), username = ref(''), password = ref(''), busy = ref(false), error = ref('')
async function submit() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await signIn({ role: role.value, username: username.value, password: password.value }); password.value = ''; await router.replace('/') }
  catch (e) { error.value = e instanceof TypeError ? '无法连接登录服务，请检查服务是否启动' : e.message }
  finally { busy.value = false }
}
</script>
<style scoped>
.login-screen { min-height: 100vh; display: flex; align-items: center; justify-content: center; gap: clamp(50px, 10vw, 200px); padding: 35px; box-sizing: border-box; background: radial-gradient(ellipse at 25% 45%, #12566a88, transparent 55%), linear-gradient(135deg,#041323,#0a263c); color: #e8f8ff; }
.login-brand > span { color: #8fd9ed; letter-spacing: 2px; font-size: 18px; }.login-brand h1 { font-size: clamp(30px,3.5vw,58px); line-height: 1.5; margin: 28px 0; }.login-brand p { color: #8badc0; letter-spacing: 5px; }
.login-card { width: 420px; max-width: 100%; padding: 38px; border: 1px solid #4ba7c366; border-radius: 14px; background: #071e32dd; box-shadow: 0 25px 80px #0005; }.login-card small { color: #59cfe4; letter-spacing: 3px; font-size: 11px; }h2 { margin: 12px 0; font-size: 30px; }.hint { color: #8eacbf; font-size: 13px; line-height: 1.7; }fieldset { border: 0; padding: 0; margin: 26px 0 20px; }legend,label { font-size: 14px; color: #c5e5ee; }legend { margin-bottom: 10px; }.roles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }button { cursor: pointer; }.roles button { padding: 12px; border: 1px solid #467389; border-radius: 5px; background: #0c2b41; color: #c3dce8; }.roles .selected { border-color: #42d6f4; background: #0a5268; color: #fff; box-shadow: inset 0 0 16px #26b5e322; }label { display: block; margin-top: 18px; }input { display: block; box-sizing: border-box; width: 100%; padding: 13px; margin-top: 9px; background: #051828; color: white; border: 1px solid #3c6177; border-radius: 5px; }input:focus { outline: 1px solid #40daef; }.submit { width: 100%; margin-top: 28px; padding: 14px; border: 1px solid #6de6ef; border-radius: 5px; background: linear-gradient(90deg,#087e9f,#11618b); color: white; font-weight: 600; }.submit:disabled { opacity: .6; cursor: wait; }.error { color: #ffb3a7; font-size: 14px; }.note { text-align: center; margin-bottom: 0; }@media(max-width:900px) { .login-brand { display: none; }.login-screen { padding: 20px; }.login-card { padding: 26px; } }
</style>

<style scoped>
@font-face { font-family: 'LoginOppo'; src: url('/hud-assets/fonts/oppo-sans-regular.ttf'); font-display: swap; }
.login-screen { position: relative; overflow: auto; font-family: 'LoginOppo', 'Microsoft YaHei', sans-serif; gap: clamp(60px,8vw,150px); padding: 130px 7vw 85px; background: radial-gradient(ellipse at 24% 57%,#06435566,transparent 52%),linear-gradient(120deg,#030f1c,#0b2033 65%,#081522); }
.login-screen::before { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .18; background-image: linear-gradient(#45788933 1px,transparent 1px),linear-gradient(90deg,#45788933 1px,transparent 1px); background-size: 65px 65px; mask-image: linear-gradient(90deg,#000,transparent 80%); }
.platform-heading { position: absolute; top: 35px; left: 5vw; right: 5vw; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid #83bfd21f; padding-bottom: 24px; }.platform-heading i { width: 30px; height: 30px; border: 1px solid #56dded; transform: rotate(45deg); background: linear-gradient(135deg,#34cbd755,#071827); box-shadow: inset 0 0 0 7px #081f33; }.platform-heading > span { font-size: clamp(17px,1.5vw,25px); font-weight: 600; letter-spacing: 1px; }.platform-heading small { margin-left: auto; color: #688d9e; letter-spacing: 2px; font-size: 10px; }
.login-brand { position: relative; width: min(600px,48vw); }.brand-kicker { font-size: 13px; letter-spacing: 4px; color: #6edbdc; border-left: 3px solid #31d7d7; padding-left: 13px; }.login-brand h1 { font-size: clamp(34px,3.4vw,55px); line-height: 1.4; letter-spacing: 2px; margin: 24px 0 18px; }.login-brand h1 em { font-style: normal; color: #6de1e5; }.login-brand p { font-size: 14px; letter-spacing: 1px; color: #8ba8b7; }
.network-art { position: relative; height: 220px; margin-top: 16px; }.network-art svg { width: 100%; height: 100%; }.node-label { position: absolute; font-size: 11px; color: #9ddfe7; padding: 5px 10px; border: 1px solid #36889866; background: #092637; }.node-label--one { top: 41%; left: 14%; }.node-label--two { top: 67%; left: 40%; }.node-label--three { top: 8%; left: 65%; }.capabilities { display: flex; gap: 35px; padding-top: 20px; border-top: 1px solid #4d829833; color: #3aa5b5; font-size: 12px; }.capabilities b { margin-left: 8px; color: #bad5df; font-size: 14px; font-weight: 400; }
.login-card { position: relative; box-sizing: border-box; width: 430px; padding: 35px; border-radius: 8px; border: 1px solid #5e8fa343; background: linear-gradient(150deg,#132e42ee,#0a1d30f2); box-shadow: 0 25px 80px #0005,inset 0 1px #b0d4e51a; }.login-card::before { content: ''; position: absolute; top: -1px; left: 35px; width: 58px; height: 3px; background: #57e2e4; box-shadow: 0 0 18px #57e2e466; }.login-card h2 { font-size: 27px; margin-top: 14px; }.login-card > small { color: #64b7c5; font-size: 10px; }.roles button { position: relative; display: flex; align-items: center; gap: 9px; text-align: left; background: #0d2335; font-size: 14px; border-color: #52768a55; }.role-icon { color: #6c9eae; }.role-check { margin-left: auto; color: #60ebea; }.roles .selected { background: #124352; border-color: #41bfc9; box-shadow: none; }.roles .selected .role-icon { color: #60ebea; }.roles button:hover { border-color: #59b8c8; }input { background: #091c2c; border-color: #47677c88; padding: 13px 15px; font-size: 14px; }input::placeholder { color: #5f7d90; }.submit { background: linear-gradient(100deg,#148995,#176a91); border-color: #45b9c9; letter-spacing: 3px; transition: filter .2s; }.submit:hover { filter: brightness(1.15); }.note { font-size: 11px; color: #708e9f; margin-top: 17px; }.page-footer { position: absolute; bottom: 23px; left: 5vw; right: 5vw; display: flex; justify-content: space-between; font-size: 11px; color: #527080; letter-spacing: 1px; }
@media(max-width:1100px) { .platform-heading small { display: none; }.login-screen { gap: 35px; padding-left: 4vw; padding-right: 4vw; }.capabilities { gap: 15px; } }
@media(max-width:900px) { .login-screen { padding: 110px 20px 70px; }.login-card { width: 420px; }.platform-heading { top: 25px; }.platform-heading > span { font-size: 16px; }.page-footer span { display: none; } }
</style>

<style scoped>
.network-art { display: flex; align-items: center; height: 190px; margin-top: 22px; padding: 0 8px; }
.flow-step { display: flex; flex-direction: column; align-items: center; position: relative; flex: 0 0 110px; gap: 11px; }
.flow-number { color: #467b8f; font-size: 11px; letter-spacing: 2px; }
.flow-step i { display: block; width: 12px; height: 12px; border: 5px solid #103f50; border-radius: 50%; background: #58d8dc; box-shadow: 0 0 0 1px #30708066; }
.flow-step--center i { box-shadow: 0 0 0 6px #3fd5df0d, 0 0 0 7px #3fd5df20; }
.flow-step strong { color: #bde9ed; font-size: 15px; font-weight: 400; letter-spacing: 1px; }
.flow-step small { color: #658b9d; font-size: 11px; }
.flow-connector { position: relative; flex: 1; min-width: 15px; height: 1px; margin-top: -25px; background: linear-gradient(90deg,#28677a44,#32859a99,#28677a44); }
.flow-connector span { position: absolute; left: 50%; top: -12px; transform: translateX(-50%); background: #0b2939; color: #518f9e; padding: 0 8px; font-size: 17px; }
@media(max-width:1100px) { .flow-step { flex-basis: 90px; } }
</style>

<style scoped>
@font-face { font-family: 'LoginHanyi'; src: url('/hud-assets/fonts/hanyi-changmeihei.ttf') format('truetype'); font-display: swap; }
@font-face { font-family: 'LoginTencent'; src: url('/hud-assets/fonts/tencent-sans-w7.otf') format('opentype'); font-display: swap; }
@font-face { font-family: 'LoginNumber'; src: url('/hud-assets/fonts/ds-digi.ttf') format('truetype'); font-display: swap; }
/* 展示标题、主标语与操作文字分别使用不同字体，形成清晰层次。 */
.platform-heading > span { font-family: 'LoginHanyi', 'LoginOppo', sans-serif; font-size: clamp(22px,1.85vw,32px); font-weight: 400; letter-spacing: 1.2px; line-height: 1.45; }
.login-brand h1 { font-family: 'LoginTencent', 'LoginOppo', sans-serif; font-size: clamp(36px,3.4vw,56px); font-weight: 400; letter-spacing: 1px; line-height: 1.5; }
.login-card h2 { font-family: 'LoginHanyi', 'LoginOppo', sans-serif; font-size: 30px; font-weight: 400; letter-spacing: 1px; }
.brand-kicker { font-family: 'LoginOppo', sans-serif; font-size: 15px; letter-spacing: 3px; }
.login-brand p { font-size: 16px; line-height: 1.8; }
.roles button, input, legend, label { font-family: 'LoginOppo', sans-serif; font-size: 16px; }
.flow-step strong { font-family: 'LoginOppo', sans-serif; font-size: 17px; }
.flow-step small { font-size: 13px; }
.flow-number { font-family: 'LoginNumber', monospace; font-size: 17px; }
.submit { font-family: 'LoginOppo', sans-serif; font-size: 18px; font-weight: 600; letter-spacing: 2px; }
.hint { font-size: 14px; }.note { font-size: 12px; }
@media(max-width:900px) { .platform-heading > span { font-size: clamp(17px,3vw,24px); }.login-card h2 { font-size: 27px; } }
</style>

<style scoped>
.network-art { height: 215px; padding: 0; }
.flow-step { flex-basis: 140px; gap: 15px; }
.flow-step strong { font-family: 'LoginHanyi', 'LoginOppo', sans-serif; font-size: 23px; font-weight: 400; letter-spacing: 2px; color: #dcf5fa; }
.flow-step small { font-size: 16px; letter-spacing: .8px; color: #8bb4c4; white-space: nowrap; }
.flow-number { font-family: 'LoginOppo', sans-serif; font-size: 15px; letter-spacing: 3px; color: #6ba8b9; }
.flow-connector { margin-top: -33px; }
.capabilities { gap: 32px; padding-top: 25px; align-items: center; font-size: 15px; }
.capabilities b { margin-left: 10px; font-family: 'LoginOppo', sans-serif; font-size: 18px; letter-spacing: 1px; color: #c6e3ec; }
@media(min-width:901px) and (max-width:1100px) { .flow-step { flex-basis: 100px; }.flow-step strong { font-size: 20px; }.flow-step small { font-size: 13px; }.capabilities { gap: 15px; }.capabilities b { font-size: 15px; } }
</style>
