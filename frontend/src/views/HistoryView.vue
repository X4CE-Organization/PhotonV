<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { useAppStore } from '../store';
import { formatDuration, formatNumber, fromNow } from '../utils';
import PaginationBar from '../components/PaginationBar.vue';
import PageHead from '../components/PageHead.vue';

const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/users/${store.user?.username}/history${query({ page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <PageHead icon="history" title="观看历史" subtitle="记录你看到哪儿了，随时接着看" />
    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>
    <p v-else-if="!items.length" class="surface p-16 text-center text-sm muted">还没有观看记录</p>
    <div v-else class="space-y-3">
      <RouterLink
        v-for="item in items"
        :key="item.id"
        :to="`/video/${item.id}`"
        class="surface flex gap-3 p-3 hover:shadow-md"
      >
        <div class="relative shrink-0">
          <img :src="item.cover" class="h-20 w-36 rounded object-cover" alt="" />
          <span class="absolute bottom-1 right-1 rounded bg-black/70 px-1 text-[11px] text-white">{{ formatDuration(item.duration) }}</span>
          <div v-if="item.duration" class="absolute bottom-0 left-0 h-0.5 bg-[var(--pv-accent)]" :style="{ width: Math.min(100, (item.progress / item.duration) * 100) + '%' }"></div>
        </div>
        <div class="min-w-0 flex-1">
          <h3 class="line-clamp-2 text-sm font-medium">{{ item.title }}</h3>
          <p class="mt-1 text-xs muted">{{ item.author.displayName }} · {{ formatNumber(item.views) }} 播放</p>
          <p class="mt-0.5 text-xs muted">
            观看到 {{ formatDuration(item.progress) }} · {{ fromNow(item.watchedAt) }}
          </p>
        </div>
      </RouterLink>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
