<template>
  <section class="hud-panel" :class="[`hud-panel--${side}`, { 'is-collapsed': collapsed }]">
    <header class="hud-panel__header">
      <span class="hud-panel__marker" aria-hidden="true"></span>
      <div class="hud-panel__heading">
        <h2>{{ title }}</h2>
        <span v-if="subtitle">{{ subtitle }}</span>
      </div>
      <span v-if="status" class="hud-panel__status" :class="`is-${statusTone}`">{{ status }}</span>
      <button
        v-if="collapsible"
        class="hud-panel__toggle"
        type="button"
        :aria-label="collapsed ? `展开${title}` : `收起${title}`"
        :aria-expanded="!collapsed"
        @click="$emit('update:collapsed', !collapsed)"
      >
        {{ collapsed ? (side === 'left' ? '›' : '‹') : (side === 'left' ? '‹' : '›') }}
      </button>
    </header>

    <div v-show="!collapsed" class="hud-panel__body">
      <slot></slot>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  status: { type: String, default: '' },
  statusTone: { type: String, default: 'online' },
  side: { type: String, default: 'left', validator: (value) => ['left', 'right'].includes(value) },
  collapsed: { type: Boolean, default: false },
  collapsible: { type: Boolean, default: true },
})

defineEmits(['update:collapsed'])
</script>

<style scoped>
.hud-panel {
  --hud-line: rgba(51, 205, 255, .75);
  --hud-glow: rgba(0, 191, 255, .24);
  position: relative;
  min-width: 0;
  color: #dff8ff;
  background:
    linear-gradient(90deg, rgba(1, 27, 56, .92), rgba(4, 39, 74, .58)),
    repeating-linear-gradient(0deg, transparent 0 27px, rgba(115, 221, 255, .035) 28px);
  border: 1px solid var(--hud-line);
  box-shadow: inset 0 0 28px var(--hud-glow), 0 0 18px rgba(0, 112, 185, .16);
  clip-path: polygon(0 13px, 13px 0, calc(100% - 13px) 0, 100% 13px, 100% calc(100% - 13px), calc(100% - 13px) 100%, 13px 100%, 0 calc(100% - 13px));
  transition: width .22s ease, min-width .22s ease, opacity .22s ease;
}

.hud-panel::before,
.hud-panel::after {
  position: absolute;
  z-index: 1;
  width: 34px;
  height: 2px;
  content: '';
  background: #69e7ff;
  box-shadow: 0 0 10px #13bbff;
}

.hud-panel::before { top: 0; left: 18px; }
.hud-panel::after { right: 18px; bottom: 0; }

.hud-panel.is-collapsed { min-width: 42px; width: 42px; }

.hud-panel__header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  min-height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(81, 212, 255, .34);
  background: linear-gradient(90deg, rgba(16, 105, 158, .4), rgba(8, 46, 91, .1));
}

.hud-panel__marker {
  width: 0;
  height: 0;
  margin-right: 7px;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 7px solid #68eaff;
  filter: drop-shadow(0 0 3px #00baff);
}

.hud-panel__heading { min-width: 0; line-height: 1.1; }
.hud-panel__heading h2 { margin: 0; color: #f1fcff; font-size: var(--font-size-panel-title); letter-spacing: .08em; font-weight: var(--font-weight-heading); }
.hud-panel__heading span { display: block; margin-top: 3px; color: #75b8d5; font-family: var(--font-family-ui); font-size: var(--font-size-assist); font-weight: var(--font-weight-body); letter-spacing: .08em; }
.hud-panel__status { margin-left: auto; padding: 3px 6px; border: 1px solid currentColor; font: 700 9px/1 Consolas, monospace; letter-spacing: .06em; }
.hud-panel__status.is-online { color: #62ffa3; background: rgba(31, 186, 107, .13); }
.hud-panel__status.is-warning { color: #ffe16e; background: rgba(255, 180, 32, .13); }
.hud-panel__status.is-alert { color: #ff8794; background: rgba(255, 64, 86, .13); }

.hud-panel__toggle {
  width: 25px;
  height: 25px;
  margin-left: 8px;
  padding: 0;
  color: #8feeff;
  border: 1px solid rgba(89, 219, 255, .62);
  background: rgba(7, 73, 123, .55);
  cursor: pointer;
  font-size: 20px;
  line-height: 18px;
}
.hud-panel__toggle:hover { color: #fff; background: rgba(24, 163, 221, .58); box-shadow: 0 0 10px rgba(51, 218, 255, .6); }
.hud-panel__body { position: relative; z-index: 1; max-height: min(68vh, 720px); padding: 12px; overflow: auto; }
.hud-panel__body::-webkit-scrollbar { width: 5px; }
.hud-panel__body::-webkit-scrollbar-thumb { background: rgba(93, 220, 255, .5); }

@media (max-width: 900px) {
  .hud-panel__heading span, .hud-panel__status { display: none; }
  .hud-panel__header { min-height: 36px; padding: 0 8px; }
}
</style>
