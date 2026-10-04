<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { api, query } from '../api';
import { useAppStore } from '../store';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';
import PageHead from '../components/PageHead.vue';

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
    <div class="space-y-3">
      <PageHead
        icon="compass"
        :title="store.categories.find((item) => item.slug === route.params.slug)?.name || '分区'"
        :subtitle="store.categories.find((item) => item.slug === route.params.slug)?.description"
      />
      <div class="flex flex-wrap gap-2 text-sm">
        <button
          v-for="item in SORTS"
          :key="item.key"
          class="rounded-lg px-3 py-1.5"
          :class="sort === item.key ? 'bg-[var(--pv-accent)]/10 font-medium text-[var(--pv-accent)]' : 'muted hover:bg-[var(--pv-surface-2)]'"
          @click="sort = item.key"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>
    <div v-else-if="!items.length" class="surface p-16 text-center text-sm muted">这个分区还没有视频</div>
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <VideoCard v-for="video in items" :key="video.id" :video="video" />
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
