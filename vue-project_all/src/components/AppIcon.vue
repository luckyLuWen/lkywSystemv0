<template>
  <svg class="app-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <template v-if="name === 'grid'"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></template>
    <template v-else-if="name === 'broadcast'"><path d="M4 14h3l6 4V6l-6 4H4z"/><path d="M16 9.5a4 4 0 0 1 0 5"/><path d="M18.5 7a7.5 7.5 0 0 1 0 10"/></template>
    <template v-else-if="name === 'radar'"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="m12 12 6-6M12 2v2M2 12h2M12 20v2M20 12h2"/></template>
    <template v-else-if="name === 'route'"><circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M7.5 16.7 10 14.2c1.2-1.2 2.8-1.2 4 0l.3.3c1.2 1.2 2.8 1.2 4 0l1.2-1.2M4.5 9.5 7 7c1.2-1.2 2.8-1.2 4 0l.3.3c1.2 1.2 2.8 1.2 4 0l1.2-1.2"/></template>
    <template v-else-if="name === 'cube'"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9"/></template>
    <template v-else-if="name === 'activity'"><path d="M3 12h4l2.2-6 4.1 12 2.4-6H21"/></template>
    <template v-else-if="name === 'shield'"><path d="M12 3 20 6v5c0 5-3.4 8.3-8 10-4.6-1.7-8-5-8-10V6zM8.5 12l2.2 2.2 4.8-4.8"/></template>
    <template v-else-if="name === 'clock'"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></template>
    <template v-else-if="name === 'chevron-left'"><path d="m14 6-6 6 6 6"/></template>
    <template v-else><circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 2.5"/></template>
  </svg>
</template>
<script setup>
defineProps({ name: { type: String, default: 'activity' } })
</script>
<style scoped>
.app-icon { width: 1em; height: 1em; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; flex: 0 0 auto; }
</style>
