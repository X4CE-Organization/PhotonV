<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { fromNow } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';

const tab = ref<'comments' | 'danmaku'>('comments');
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const keyword = ref('');
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(
      `/api/admin/${tab.value}${query({ q: keyword.value, page: page.value })}`,
    );
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
  } finally {
    loading.value = false;
  }
}

async function remove(item: any) {
  if (!window.confirm('确定删除这条内容吗？')) return;
  if (tab.value === 'comments') await api.del(`/api/admin/comments/${item.id}`);
  else await api.del(`/api/danmaku/${item.id}`);
  toast.success('已删除');
  void load();
}

function switchTab(value: 'comments' | 'danmaku') {
  tab.value = value;
  page.value = 1;
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">评论与弹幕</h1>
      <div class="flex gap-2 text-sm">
        <button :class="tab === 'comments' ? 'font-semibold text-primary' : 'text-slate-500'" @click="switchTab('comments')">评论</button>
        <button :class="tab === 'danmaku' ? 'font-semibold text-primary' : 'text-slate-500'" @click="switchTab('danmaku')">弹幕</button>
      </div>
    </div>

    <div class="card flex items-center gap-2 p-3">
      <input v-model="keyword" class="input !w-64" placeholder="搜索内容" @keyup.enter="page = 1; load()" />
      <button class="btn-ghost" @click="page = 1; load()">查询</button>
      <span class="ml-auto text-xs text-slate-400">共 {{ total }} 条</span>
    </div>

    <div class="card overflow-x-auto">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">加载中…</p>
      <table v-else class="table-base">
        <thead>
          <tr>
            <th>内容</th>
            <th class="w-32">用户</th>
            <th class="w-32">所属视频</th>
            <th class="w-28">时间点</th>
            <th class="w-28">发布时间</th>
            <th class="w-20">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>
              <span class="text-sm">{{ item.content }}</span>
              <span v-if="item.color" class="ml-2" :style="{ color: item.color }">●</span>
            </td>
            <td class="text-xs">
              <RouterLink :to="`/space/${item.user?.username}`" class="hover:text-primary">{{ item.user?.displayName }}</RouterLink>
            </td>
            <td class="text-xs">
              <RouterLink :to="`/video/${item.videoId}`" class="line-clamp-1 hover:text-primary">{{ item.videoTitle || `#${item.videoId}` }}</RouterLink>
            </td>
            <td class="text-xs text-slate-400">{{ item.time !== undefined ? `${Number(item.time).toFixed(1)}s` : '—' }}</td>
            <td class="text-xs text-slate-400">{{ fromNow(item.createdAt) }}</td>
            <td><button class="text-xs text-rose-500 hover:underline" @click="remove(item)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
