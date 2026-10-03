<script setup lang="ts">
import { toasts } from '../composables/toast';
</script>

<template>
  <div class="pointer-events-none fixed bottom-6 left-1/2 z-[100] flex w-max max-w-[92vw] -translate-x-1/2 flex-col items-center gap-2">
    <div
      v-for="item in toasts"
      :key="item.id"
      class="pointer-events-auto rounded-full px-4 py-2 text-sm text-white backdrop-blur"
      :class="item.kind === 'error' ? 'bg-rose-500/95' : item.kind === 'success' ? 'bg-emerald-500/95' : 'bg-slate-900/90'"
    >
      {{ item.message }}
    </div>
  </div>
</template>
