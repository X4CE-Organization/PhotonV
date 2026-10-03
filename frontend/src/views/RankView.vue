<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { formatNumber, initials } from '../utils';
import VideoCard from '../components/VideoCard.vue';

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
    <div class="card flex flex-wrap items-center justify-between gap-3 p-4">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="item in TYPES"
          :key="item.key"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="type === item.key ? 'bg-primary/10 font-medium text-primary' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
          @click="type = item.key"
        >
          {{ item.label }}
        </button>
      </div>
      <div v-if="type !== 'fans'" class="flex gap-2 text-xs">
        <button :class="period === 'all' ? 'text-primary' : 'text-slate-400'" @click="period = 'all'">总榜</button>
        <button :class="period === 'week' ? 'text-primary' : 'text-slate-400'" @click="period = 'week'">周榜</button>
      </div>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm text-slate-400">加载中…</p>

    <div v-else-if="type === 'fans'" class="card divide-y divide-slate-100 dark:divide-slate-800">
      <RouterLink
        v-for="(user, index) in users"
        :key="user.id"
        :to="`/space/${user.username}`"
        class="flex items-center gap-3 p-3 hover:bg-slate-50 dark:hover:bg-slate-800/60"
      >
        <span class="w-6 text-center text-sm font-semibold" :class="index < 3 ? 'text-primary' : 'text-slate-400'">{{ index + 1 }}</span>
        <img v-if="user.avatar" :src="user.avatar" class="h-10 w-10 rounded-full object-cover" alt="" />
        <span v-else class="grid h-10 w-10 place-items-center rounded-full bg-primary/15 font-semibold text-primary">
          {{ initials(user.displayName) }}
        </span>
        <div class="min-w-0 flex-1">
          <div class="font-medium">{{ user.displayName }}</div>
          <p class="text-xs text-slate-400">{{ formatNumber(user.followerCount) }} 粉丝 · {{ user.videoCount }} 投稿</p>
        </div>
        <span class="text-xs text-slate-400">{{ formatNumber(user.playCount) }} 播放</span>
      </RouterLink>
    </div>

    <template v-else>
      <p v-if="!items.length" class="card p-16 text-center text-sm text-slate-400">暂无数据</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in items" :key="video.id" :video="video" />
      </div>
    </template>
  </div>
</template>
