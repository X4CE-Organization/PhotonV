<script setup lang="ts">
import { toasts } from '../composables/toast';
</script>

<template>
  <div class="pointer-events-none fixed right-4 top-16 z-[100] flex w-72 flex-col gap-2">
    <div
      v-for="item in toasts"
      :key="item.id"
      class="pointer-events-auto rounded-lg px-3 py-2 text-sm text-white shadow-lg"
      :class="item.kind === 'error' ? 'bg-rose-500' : item.kind === 'success' ? 'bg-emerald-500' : 'bg-slate-800'"
    >
      {{ item.message }}
    </div>
  </div>
</template>
