<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { formatNumber, initials } from '../utils';
import VideoCard from '../components/VideoCard.vue';
import PageHead from '../components/PageHead.vue';

const type = ref('views');
const period = ref('all');
const items = ref<any[]>([]);
const users = ref<any[]>([]);
const loading = ref(true);

const TYPES = [
  { key: 'views', label: '播放榜' },
  { key: 'likes', label: '点赞榜' },
  { key: 'coins', label: '投币榜' },
  { key: 'favorites', label: '收藏榜' },
  { key: 'comments', label: '评论榜' },
  { key: 'fans', label: '粉丝榜' },
];

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/rank${query({ type: type.value, period: period.value, limit: 30 })}`);
    items.value = data.items || [];
    users.value = data.users || [];
  } finally {
    loading.value = false;
  }
}

watch([type, period], load);
onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <PageHead icon="flame" title="排行榜" subtitle="按播放、点赞、投币、收藏、评论与粉丝数排出来的榜单" />
    <div class="surface flex flex-wrap items-center justify-between gap-3 p-3">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="item in TYPES"
          :key="item.key"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="type === item.key ? 'bg-[var(--pv-accent)]/10 font-medium text-[var(--pv-accent)]' : 'muted hover:bg-[var(--pv-surface-2)]'"
          @click="type = item.key"
        >
          {{ item.label }}
        </button>
      </div>
      <div v-if="type !== 'fans'" class="flex gap-2 text-xs">
        <button :class="period === 'all' ? 'text-[var(--pv-accent)]' : 'muted'" @click="period = 'all'">总榜</button>
        <button :class="period === 'week' ? 'text-[var(--pv-accent)]' : 'muted'" @click="period = 'week'">周榜</button>
      </div>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>

    <div v-else-if="type === 'fans'" class="surface divide-y divide-[var(--pv-border)]">
      <RouterLink
        v-for="(user, index) in users"
        :key="user.id"
        :to="`/space/${user.username}`"
        class="flex items-center gap-3 p-3 hover:bg-[var(--pv-surface-2)]"
      >
        <span class="w-6 text-center text-sm font-semibold" :class="index < 3 ? 'text-[var(--pv-accent)]' : 'muted'">{{ index + 1 }}</span>
        <img v-if="user.avatar" :src="user.avatar" class="h-10 w-10 rounded-full object-cover" alt="" />
        <span v-else class="grid h-10 w-10 place-items-center rounded-full bg-[var(--pv-accent)]/15 font-semibold text-[var(--pv-accent)]">
          {{ initials(user.displayName) }}
        </span>
        <div class="min-w-0 flex-1">
          <div class="font-medium">{{ user.displayName }}</div>
          <p class="text-xs muted">{{ formatNumber(user.followerCount) }} 粉丝 · {{ user.videoCount }} 投稿</p>
        </div>
        <span class="text-xs muted">{{ formatNumber(user.playCount) }} 播放</span>
      </RouterLink>
    </div>

    <template v-else>
      <p v-if="!items.length" class="surface p-16 text-center text-sm muted">暂无数据</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in items" :key="video.id" :video="video" />
      </div>
    </template>
  </div>
</template>
