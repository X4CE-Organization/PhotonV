<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ page: number; size: number; total: number }>();
const emit = defineEmits<{ (event: 'change', page: number): void }>();

const pages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(1, props.size))));
const list = computed(() => {
  const total = pages.value;
  const start = Math.max(1, Math.min(props.page - 2, total - 4));
  const end = Math.min(total, start + 4);
  const items: number[] = [];
  for (let index = start; index <= end; index += 1) items.push(index);
  return items;
});
</script>

<template>
  <div v-if="pages > 1" class="flex items-center justify-center gap-2 py-6 text-sm">
    <button class="btn-ghost !px-2 !py-1" :disabled="page <= 1" @click="emit('change', page - 1)">上一页</button>
    <button
      v-for="item in list"
      :key="item"
      class="btn !px-3 !py-1"
      :class="item === page ? 'bg-primary text-white' : 'border border-slate-200 dark:border-slate-700'"
      @click="emit('change', item)"
    >
      {{ item }}
    </button>
    <button class="btn-ghost !px-2 !py-1" :disabled="page >= pages" @click="emit('change', page + 1)">下一页</button>
    <span class="ml-2 text-xs text-slate-400">共 {{ total }} 条</span>
  </div>
</template>
