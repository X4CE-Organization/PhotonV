<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { useAppStore } from '../store';
import { formatNumber, initials } from '../utils';
import Icon from '../components/Icon.vue';

const store = useAppStore();
const items = ref<any[]>([]);
const loading = ref(true);
const status = ref('live');
const mine = ref<any>(null);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/live/rooms${query({ status: status.value, size: 48 })}`);
    items.value = data.items || [];
    if (store.isLogin) {
      try {
        mine.value = await api.get<any>('/api/live/mine');
      } catch {
        mine.value = null;
      }
    }
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="surface flex flex-wrap items-center justify-between gap-3 p-4">
      <div>
        <h1 class="flex items-center gap-2 text-lg font-bold">
          <Icon name="radio" :size="20" class="text-[var(--pv-accent)]" />直播
        </h1>
        <p class="mt-1 text-xs muted">{{ store.settings.live_notice }}</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex rounded-full bg-[var(--pv-surface-2)] p-0.5 text-xs">
          <button class="rounded-full px-3 py-1.5" :class="status === 'live' ? 'bg-[var(--pv-surface)] font-medium' : 'muted'" @click="status = 'live'; load()">正在直播</button>
          <button class="rounded-full px-3 py-1.5" :class="status === 'all' ? 'bg-[var(--pv-surface)] font-medium' : 'muted'" @click="status = 'all'; load()">全部房间</button>
        </div>
        <RouterLink v-if="store.isLogin" to="/live/0" class="btn-ghost text-xs">
          <Icon name="settings" :size="15" />我的直播间
        </RouterLink>
      </div>
    </div>

    <div v-if="mine?.room" class="surface flex flex-wrap items-center gap-3 p-4">
      <span class="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-white">
        <Icon name="radio" :size="19" />
      </span>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium">{{ mine.room.title }}</div>
        <div class="text-xs muted">
          状态：{{ mine.room.status === 'live' ? '直播中' : mine.room.status === 'banned' ? '已封禁' : '未开播' }}
          · 累计观众 {{ formatNumber(mine.room.totalViewers) }}
        </div>
      </div>
      <RouterLink :to="`/live/${mine.room.id}`" class="btn-primary text-xs">进入我的直播间</RouterLink>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>
    <p v-else-if="!items.length" class="surface p-16 text-center text-sm muted">
      还没有人开播，{{ store.isLogin ? '去申请直播权限成为第一个主播吧' : '登录后可以申请开播' }}
    </p>
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
      <RouterLink
        v-for="room in items"
        :key="room.id"
        :to="`/live/${room.id}`"
        class="group overflow-hidden rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] transition hover:-translate-y-0.5"
      >
        <div class="relative aspect-video overflow-hidden bg-[var(--pv-surface-2)]">
          <img v-if="room.cover" :src="room.cover" class="h-full w-full object-cover transition group-hover:scale-105" alt="" />
          <div v-else class="grid h-full w-full place-items-center muted"><Icon name="radio" :size="26" /></div>
          <span
            class="absolute left-2 top-2 rounded-md px-2 py-0.5 text-[11px] font-semibold text-white"
            :class="room.status === 'live' ? 'bg-rose-500' : 'bg-slate-700/80'"
          >
            {{ room.status === 'live' ? '直播中' : '未开播' }}
          </span>
          <span class="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
            {{ formatNumber(room.viewers) }} 人在看
          </span>
        </div>
        <div class="space-y-1.5 p-3">
          <h3 class="line-clamp-1 text-sm font-medium">{{ room.title }}</h3>
          <div class="flex items-center gap-2 text-xs muted">
            <img v-if="room.owner?.avatar" :src="room.owner.avatar" class="h-5 w-5 rounded-full object-cover" alt="" />
            <span v-else class="grid h-5 w-5 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-[10px] font-bold text-white">
              {{ initials(room.owner?.displayName) }}
            </span>
            <span class="truncate">{{ room.owner?.displayName }}</span>
            <span v-if="room.owner?.membershipLevel" class="ml-auto chip !py-0 text-[10px]">会员</span>
          </div>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
