<template>
  <div class="hud-dashboard-shell">
    <aside class="hud-dashboard-shell__side hud-dashboard-shell__side--left">
      <slot name="left"></slot>
    </aside>
    <main class="hud-dashboard-shell__content"><slot></slot></main>
    <aside class="hud-dashboard-shell__side hud-dashboard-shell__side--right">
      <slot name="right"></slot>
    </aside>
    <footer class="hud-dashboard-shell__bottom"><slot name="bottom"></slot></footer>
  </div>
</template>

<style scoped>
.hud-dashboard-shell { position: relative; display: grid; grid-template-columns: minmax(220px, 19vw) minmax(0, 1fr) minmax(220px, 19vw); min-height: 100%; padding: 12px 16px 62px; gap: 14px; box-sizing: border-box; overflow: hidden; }
.hud-dashboard-shell__side { position: relative; z-index: 2; min-width: 0; }
.hud-dashboard-shell__content { position: relative; z-index: 1; min-width: 0; min-height: 0; }
.hud-dashboard-shell__bottom { position: absolute; right: 16px; bottom: 0; left: 16px; z-index: 3; }
@media (max-width: 960px) { .hud-dashboard-shell { grid-template-columns: minmax(180px, 28vw) minmax(0, 1fr); } .hud-dashboard-shell__side--right { display: none; } }
@media (max-width: 680px) { .hud-dashboard-shell { display: block; padding: 8px 8px 58px; overflow: auto; } .hud-dashboard-shell__side--left { margin-bottom: 10px; } .hud-dashboard-shell__bottom { right: 8px; left: 8px; } }
</style>
