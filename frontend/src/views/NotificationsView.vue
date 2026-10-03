<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { useAppStore } from '../store';
import { fromNow, initials } from '../utils';

const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const unread = ref(0);
const type = ref('all');
const page = ref(1);
const size = ref(20);
const loading = ref(true);

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'reply', label: '回复我的' },
  { key: 'like', label: '收到的赞' },
  { key: 'coin', label: '投币' },
  { key: 'follow', label: '新增粉丝' },
  { key: 'review', label: '投稿审核' },
  { key: 'system', label: '系统通知' },
];

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/notifications${query({ type: type.value, page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    unread.value = data.unreadTotal || 0;
    size.value = data.size || 20;
    store.unread = unread.value;
  } finally {
    loading.value = false;
  }
}

async function markAll() {
  await api.post('/api/notifications/read', { all: true });
  store.unread = 0;
  void load();
}

function link(item: any): string {
  if (item.refType === 'video') return `/video/${item.refId}`;
  if (item.refType === 'user') return `/space/${item.from?.username || ''}`;
  return '/notifications';
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">消息 <span v-if="unread" class="text-xs text-rose-500">（{{ unread }} 条未读）</span></h1>
      <button class="btn-ghost text-xs" @click="markAll">全部标记已读</button>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="item in TABS"
        :key="item.key"
        class="rounded-lg px-3 py-1.5 text-sm"
        :class="type === item.key ? 'bg-primary/10 font-medium text-primary' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
        @click="type = item.key; page = 1; load()"
      >
        {{ item.label }}
      </button>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm text-slate-400">加载中…</p>
    <p v-else-if="!items.length" class="card p-16 text-center text-sm text-slate-400">暂时没有消息</p>
    <ul v-else class="card divide-y divide-slate-100 dark:divide-slate-800">
      <li v-for="item in items" :key="item.id" class="flex gap-3 p-3">
        <img v-if="item.from?.avatar" :src="item.from.avatar" class="h-9 w-9 rounded-full object-cover" alt="" />
        <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
          {{ initials(item.from?.displayName || item.type) }}
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2 text-sm">
            <RouterLink :to="link(item)" class="font-medium hover:text-primary">{{ item.title }}</RouterLink>
            <span v-if="!item.isRead" class="rounded bg-rose-500/10 px-1 text-[10px] text-rose-500">未读</span>
          </div>
          <p v-if="item.content" class="mt-0.5 line-clamp-2 text-xs text-slate-500">{{ item.content }}</p>
          <p class="mt-0.5 text-[11px] text-slate-400">{{ fromNow(item.createdAt) }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
