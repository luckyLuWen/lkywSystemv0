<template>
  <nav class="hud-bottom-nav" aria-label="场景导航">
    <button
      v-for="item in items"
      :key="item.key"
      class="hud-bottom-nav__item"
      :class="{ 'is-active': modelValue === item.key }"
      type="button"
      :aria-current="modelValue === item.key ? 'page' : undefined"
      @click="select(item.key)"
    >
      <span class="hud-bottom-nav__icon" aria-hidden="true">{{ item.icon || '◆' }}</span>
      <span>{{ item.label }}</span>
    </button>
  </nav>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'change'])

function select(key) {
  emit('update:modelValue', key)
  emit('change', key)
}
</script>

<style scoped>
.hud-bottom-nav {
  display: flex;
  align-items: end;
  justify-content: center;
  gap: clamp(3px, .7vw, 12px);
  min-height: 56px;
  padding: 0 26px 7px;
  background: linear-gradient(180deg, rgba(1, 16, 37, 0), rgba(2, 22, 47, .92) 50%);
  border-top: 1px solid rgba(55, 205, 255, .4);
}
.hud-bottom-nav__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 78px;
  min-height: 31px;
  padding: 0 12px;
  color: #8ab9d1;
  border: 1px solid transparent;
  border-bottom: 0;
  background: linear-gradient(135deg, rgba(20, 91, 144, .26), rgba(5, 21, 48, .3));
  clip-path: polygon(10px 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 10px 100%, 0 50%);
  cursor: pointer;
  font: var(--font-weight-heading) var(--font-size-body)/1 var(--font-family-ui);
  letter-spacing: .04em;
  transition: color .18s ease, background .18s ease, filter .18s ease;
}
.hud-bottom-nav__item::after { position: absolute; right: 18%; bottom: -4px; left: 18%; height: 2px; content: ''; background: transparent; }
.hud-bottom-nav__item:hover { color: #d9faff; background: rgba(23, 141, 207, .34); }
.hud-bottom-nav__item.is-active { color: #fff4ad; border-color: rgba(255, 221, 85, .9); background: linear-gradient(135deg, rgba(169, 126, 17, .75), rgba(86, 59, 8, .56)); filter: drop-shadow(0 0 7px rgba(255, 207, 63, .43)); }
.hud-bottom-nav__item.is-active::after { background: #ffda50; box-shadow: 0 0 8px #ffd43b; }
.hud-bottom-nav__icon { color: #62dcff; font-size: 12px; }
.hud-bottom-nav__item.is-active .hud-bottom-nav__icon { color: #fff6b2; }
@media (max-width: 680px) { .hud-bottom-nav { justify-content: flex-start; padding-right: 8px; padding-left: 8px; overflow-x: auto; } .hud-bottom-nav__item { flex: 0 0 auto; min-width: 68px; padding: 0 9px; font-size: 11px; } }
</style>
