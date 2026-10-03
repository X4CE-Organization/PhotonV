<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { api, query } from '../api';
import { useAppStore } from '../store';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';

const route = useRoute();
const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(24);
const sort = ref('new');
const loading = ref(true);

const SORTS = [
  { key: 'new', label: '最新发布' },
  { key: 'hot', label: '最多播放' },
  { key: 'like', label: '最多点赞' },
  { key: 'coin', label: '最多投币' },
  { key: 'comment', label: '最多评论' },
];

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(
      `/api/videos${query({ category: route.params.slug, sort: sort.value, page: page.value })}`,
    );
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 24;
  } finally {
    loading.value = false;
  }
}

watch([() => route.params.slug, sort], () => {
  page.value = 1;
  void load();
});
onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="card flex flex-wrap items-center justify-between gap-3 p-4">
      <div>
        <h1 class="text-base font-semibold">
          {{ store.categories.find((item) => item.slug === route.params.slug)?.icon }}
          {{ store.categories.find((item) => item.slug === route.params.slug)?.name || '分区' }}
        </h1>
        <p class="mt-1 text-xs text-slate-500">
          {{ store.categories.find((item) => item.slug === route.params.slug)?.description }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2 text-sm">
        <button
          v-for="item in SORTS"
          :key="item.key"
          class="rounded-lg px-3 py-1.5"
          :class="sort === item.key ? 'bg-primary/10 font-medium text-primary' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
          @click="sort = item.key"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm text-slate-400">加载中…</p>
    <div v-else-if="!items.length" class="card p-16 text-center text-sm text-slate-400">这个分区还没有视频</div>
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <VideoCard v-for="video in items" :key="video.id" :video="video" />
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
