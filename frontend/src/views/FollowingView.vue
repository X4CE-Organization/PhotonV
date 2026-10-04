<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../api';
import { useAppStore } from '../store';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';
import PageHead from '../components/PageHead.vue';

const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(24);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/following-feed${query({ page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 24;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <PageHead icon="users" title="我的关注" subtitle="这里是你关注的人最近发布的视频">
      <template #actions>
        <RouterLink :to="`/space/${store.user?.username}`" class="btn-ghost text-xs">管理关注列表</RouterLink>
      </template>
    </PageHead>
    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>
    <p v-else-if="!items.length" class="surface p-16 text-center text-sm muted">
      还没有关注的人，去首页逛逛吧
    </p>
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <VideoCard v-for="video in items" :key="video.id" :video="video" />
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
