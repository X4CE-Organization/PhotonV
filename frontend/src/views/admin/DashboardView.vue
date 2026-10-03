<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api } from '../../api';
import { formatNumber, fromNow } from '../../utils';
import VideoCard from '../../components/VideoCard.vue';

const data = ref<any>(null);
const loading = ref(true);

const cards = computed(() => {
  if (!data.value) return [];
  return [
    { label: '用户总数', value: data.value.users.total, sub: `本周新增 ${data.value.users.newWeek} · 封禁 ${data.value.users.banned}`, to: '/admin/users' },
    { label: '视频总数', value: data.value.videos.total, sub: `已公开 ${data.value.videos.published} · 待审 ${data.value.videos.pending}`, to: '/admin/videos' },
    { label: '总播放', value: formatNumber(data.value.interactions.views), sub: `点赞 ${formatNumber(data.value.interactions.likes)}`, to: '/admin/videos' },
    { label: '弹幕', value: formatNumber(data.value.interactions.danmaku), sub: `评论 ${formatNumber(data.value.interactions.comments)}`, to: '/admin/comments' },
    { label: '待处理举报', value: data.value.reports.pending, sub: `累计举报 ${data.value.reports.total}`, to: '/admin/reports' },
    { label: '投币总数', value: formatNumber(data.value.interactions.coins), sub: `收藏 ${formatNumber(data.value.interactions.favorites)}`, to: '/admin/videos' },
  ];
});

const maxTrend = computed(() => Math.max(1, ...(data.value?.trend || []).map((item: any) => item.count)));

onMounted(async () => {
  try {
    data.value = await api.get<any>('/api/admin/dashboard');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中…</p>
  <div v-else-if="data" class="space-y-4">
    <h1 class="text-base font-semibold">控制面板</h1>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <RouterLink v-for="card in cards" :key="card.label" :to="card.to" class="card p-4 hover:shadow-md">
        <div class="text-xs text-slate-400">{{ card.label }}</div>
        <div class="mt-1 text-2xl font-bold text-primary">{{ card.value }}</div>
        <div class="mt-1 text-xs text-slate-500">{{ card.sub }}</div>
      </RouterLink>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="card p-4">
        <h2 class="text-sm font-semibold">近 14 天投稿趋势</h2>
        <div class="mt-4 flex h-40 items-end gap-1">
          <div v-for="item in data.trend" :key="item.day" class="flex flex-1 flex-col items-center gap-1">
            <div class="w-full rounded-t bg-primary/70" :style="{ height: `${(item.count / maxTrend) * 100}%`, minHeight: '4px' }"></div>
            <span class="text-[10px] text-slate-400">{{ item.day.slice(5) }}</span>
          </div>
          <p v-if="!data.trend.length" class="text-xs text-slate-400">暂无数据</p>
        </div>
      </section>

      <section class="card p-4">
        <h2 class="text-sm font-semibold">最近管理操作</h2>
        <ul class="mt-3 space-y-2 text-xs">
          <li v-for="item in data.recentActions" :key="item.id" class="flex items-center gap-2">
            <span class="font-mono text-slate-400">{{ item.action }}</span>
            <span class="text-slate-500">{{ item.actor }}</span>
            <span class="ml-auto text-slate-400">{{ fromNow(item.createdAt) }}</span>
          </li>
          <li v-if="!data.recentActions.length" class="text-slate-400">暂无记录</li>
        </ul>
      </section>
    </div>

    <section>
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">待审核视频（{{ data.videos.pending }}）</h2>
        <RouterLink to="/admin/videos" class="text-xs text-primary">全部 →</RouterLink>
      </div>
      <p v-if="!data.pendingVideos.length" class="card p-8 text-center text-sm text-slate-400">没有待审核的投稿</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <VideoCard v-for="video in data.pendingVideos" :key="video.id" :video="video" />
      </div>
    </section>

    <section class="card p-4">
      <h2 class="text-sm font-semibold">最新注册用户</h2>
      <ul class="mt-3 space-y-2 text-sm">
        <li v-for="user in data.recentUsers" :key="user.id" class="flex items-center gap-2">
          <RouterLink :to="`/space/${user.username}`" class="hover:text-primary">{{ user.displayName }}</RouterLink>
          <span class="text-xs text-slate-400">@{{ user.username }}</span>
          <span class="ml-auto text-xs text-slate-400">{{ fromNow(user.createdAt) }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>
