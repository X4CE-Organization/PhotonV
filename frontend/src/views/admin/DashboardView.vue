<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api } from '../../api';
import { formatNumber, fromNow } from '../../utils';
import VideoCard from '../../components/VideoCard.vue';
import Icon from '../../components/Icon.vue';

const data = ref<any>(null);
const loading = ref(true);

const kpis = computed(() => {
  if (!data.value) return [];
  const { users, videos, interactions, live } = data.value;
  return [
    {
      label: '注册用户',
      value: users.total,
      note: `本周 +${users.newWeek}`,
      extra: users.banned ? `封禁 ${users.banned}` : '无封禁',
      icon: 'users',
      to: '/admin/users',
    },
    {
      label: '视频存量',
      value: videos.total,
      note: `本周 +${videos.newWeek}`,
      extra: `驳回 ${videos.rejected}`,
      icon: 'film',
      to: '/admin/videos',
    },
    {
      label: '累计播放',
      value: formatNumber(interactions.views),
      note: `点赞 ${formatNumber(interactions.likes)}`,
      extra: `收藏 ${formatNumber(interactions.favorites)}`,
      icon: 'play',
      to: '/admin/videos',
    },
    {
      label: '互动总量',
      value: formatNumber(interactions.comments + interactions.danmaku),
      note: `评论 ${formatNumber(interactions.comments)}`,
      extra: `弹幕 ${formatNumber(interactions.danmaku)}`,
      icon: 'message',
      to: '/admin/comments',
    },
  ];
});

const todos = computed(() => {
  if (!data.value) return [];
  return [
    { label: '待审核投稿', value: data.value.videos.pending, to: '/admin/videos', icon: 'film' },
    { label: '待处理举报', value: data.value.reports.pending, to: '/admin/reports', icon: 'flag' },
    { label: '待确认订单', value: data.value.orders.pending, to: '/admin/orders', icon: 'card' },
  ];
});

/** 没有待办时不占版面，避免一屏全是 0 */
const pendingTodos = computed(() => todos.value.filter((item) => item.value > 0));

const maxTrend = computed(() => Math.max(1, ...(data.value?.trend || []).map((item: any) => item.count)));

const health = computed(() => {
  if (!data.value) return [];
  const system = data.value.system;
  return [
    {
      label: 'Redis',
      ok: Boolean(system.redis?.enabled ?? system.redis?.connected),
      text: system.redis?.enabled ?? system.redis?.connected ? '已连接' : '未启用（走内存）',
    },
    {
      label: 'ffmpeg',
      ok: Boolean(system.ffmpeg?.available),
      text: system.ffmpeg?.available ? '可用' : '未安装（跳过转码）',
    },
    {
      label: '转码队列',
      ok: (system.transcoding || 0) + (system.transcodePending || 0) === 0,
      text: `进行中 ${system.transcoding || 0} · 排队 ${system.transcodePending || 0}`,
    },
    {
      label: '实时连接',
      ok: true,
      text: `${system.websocket?.connections || 0} 条 WebSocket`,
    },
  ];
});

const revenue = computed(() => ((data.value?.orders?.revenueCents || 0) / 100).toFixed(2));

onMounted(async () => {
  try {
    data.value = await api.get<any>('/api/admin/dashboard');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <div v-else-if="data" class="space-y-4">
    <!-- 待办：只有真的有事才出现 -->
    <section v-if="pendingTodos.length" class="grid gap-2 sm:grid-cols-3">
      <RouterLink
        v-for="item in pendingTodos"
        :key="item.label"
        :to="item.to"
        class="pv-console-tile flex items-center gap-3 border-[var(--pv-accent)]/40 transition hover:-translate-y-0.5"
      >
        <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--pv-accent)]/15 text-[var(--pv-accent)]">
          <Icon :name="item.icon" :size="17" />
        </span>
        <div class="min-w-0">
          <p class="text-xs muted">{{ item.label }}</p>
          <p class="pv-console-kpi">{{ item.value }}</p>
        </div>
        <span class="ml-auto rounded-full bg-[var(--pv-accent)] px-2 py-0.5 text-[10px] font-semibold text-white">待办</span>
      </RouterLink>
    </section>

    <!-- 指标 -->
    <section class="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <RouterLink v-for="card in kpis" :key="card.label" :to="card.to" class="pv-console-tile transition hover:-translate-y-0.5">
        <div class="flex items-center gap-2 text-xs muted">
          <Icon :name="card.icon" :size="14" />{{ card.label }}
        </div>
        <p class="pv-console-kpi mt-2">{{ card.value }}</p>
        <p class="mt-1 flex flex-wrap items-center gap-x-2 text-[11px] muted">
          <span>{{ card.note }}</span>
          <span class="opacity-60">·</span>
          <span>{{ card.extra }}</span>
        </p>
      </RouterLink>
    </section>

    <div class="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <!-- 趋势：横向条 -->
      <section class="pv-console-tile">
        <header class="flex items-center justify-between">
          <h2 class="text-sm font-semibold">近 14 天投稿</h2>
          <span class="text-[11px] muted">峰值 {{ maxTrend }}</span>
        </header>
        <div class="mt-3 space-y-1.5">
          <div v-for="item in data.trend" :key="item.day" class="flex items-center gap-2 text-[11px]">
            <span class="w-12 shrink-0 font-mono muted">{{ item.day.slice(5) }}</span>
            <span class="pv-console-bar-track flex-1"><span :style="{ width: `${(item.count / maxTrend) * 100}%` }"></span></span>
            <span class="w-6 shrink-0 text-right font-medium">{{ item.count }}</span>
          </div>
          <p v-if="!data.trend.length" class="py-6 text-center text-xs muted">暂无投稿数据</p>
        </div>
      </section>

      <!-- 运行状态 -->
      <section class="pv-console-tile">
        <h2 class="text-sm font-semibold">运行状态</h2>
        <ul class="mt-3 space-y-2">
          <li v-for="item in health" :key="item.label" class="flex items-center gap-2 text-xs">
            <span class="h-1.5 w-1.5 rounded-full" :class="item.ok ? 'bg-emerald-500' : 'bg-amber-500'"></span>
            <span class="font-medium">{{ item.label }}</span>
            <span class="ml-auto muted">{{ item.text }}</span>
          </li>
        </ul>
        <div class="mt-4 grid grid-cols-3 gap-2 text-center">
          <div class="rounded-xl bg-[var(--pv-surface-2)] px-2 py-2">
            <p class="text-[10px] muted">直播中</p>
            <p class="text-base font-semibold">{{ data.live.living }}</p>
          </div>
          <div class="rounded-xl bg-[var(--pv-surface-2)] px-2 py-2">
            <p class="text-[10px] muted">累计收入</p>
            <p class="text-base font-semibold">¥{{ revenue }}</p>
          </div>
          <div class="rounded-xl bg-[var(--pv-surface-2)] px-2 py-2">
            <p class="text-[10px] muted">投币</p>
            <p class="text-base font-semibold">{{ formatNumber(data.interactions.coins) }}</p>
          </div>
        </div>
      </section>
    </div>

    <!-- 待审核视频：有内容才占版面 -->
    <section v-if="data.pendingVideos.length">
      <div class="mb-2 flex items-center gap-2">
        <h2 class="text-sm font-semibold">待审核投稿</h2>
        <span class="chip !py-0 text-[10px]">{{ data.videos.pending }}</span>
        <RouterLink to="/admin/videos" class="ml-auto text-xs text-[var(--pv-accent)]">全部 →</RouterLink>
      </div>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <VideoCard v-for="video in data.pendingVideos" :key="video.id" :video="video" />
      </div>
    </section>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- 时间线 -->
      <section class="pv-console-tile">
        <h2 class="text-sm font-semibold">最近管理动作</h2>
        <ol class="mt-3 space-y-2.5">
          <li v-for="item in data.recentActions" :key="item.id" class="flex items-start gap-2.5 text-xs">
            <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--pv-accent)]"></span>
            <div class="min-w-0 flex-1">
              <p class="truncate">
                <span class="font-medium">{{ item.actor }}</span>
                <span class="ml-1 font-mono text-[11px] muted">{{ item.action }}</span>
              </p>
              <p class="text-[11px] muted">
                {{ item.targetType }}{{ item.targetId ? ` #${item.targetId}` : '' }} · {{ fromNow(item.createdAt) }}
              </p>
            </div>
          </li>
          <li v-if="!data.recentActions.length" class="text-xs muted">暂无记录</li>
        </ol>
      </section>

      <section class="pv-console-tile">
        <h2 class="text-sm font-semibold">最新注册</h2>
        <ul class="mt-3 space-y-2.5">
          <li v-for="user in data.recentUsers" :key="user.id" class="flex items-center gap-2.5 text-xs">
            <img v-if="user.avatar" :src="user.avatar" class="h-7 w-7 rounded-full object-cover" alt="" />
            <span v-else class="grid h-7 w-7 place-items-center rounded-full bg-[var(--pv-accent)]/15 text-[11px] font-semibold text-[var(--pv-accent)]">
              {{ (user.displayName || '?').slice(0, 1) }}
            </span>
            <RouterLink :to="`/space/${user.username}`" class="hover:text-[var(--pv-accent)]">
              {{ user.displayName }}
            </RouterLink>
            <span class="muted">@{{ user.username }}</span>
            <span class="ml-auto text-[11px] muted">{{ fromNow(user.createdAt) }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
