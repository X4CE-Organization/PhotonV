<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../../api';
import { fromNow } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';

const tab = ref<'audit' | 'login'>('audit');
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(50);
const keyword = ref('');
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const url =
      tab.value === 'audit'
        ? `/api/admin/logs/audit${query({ q: keyword.value, page: page.value })}`
        : `/api/admin/logs/login${query({ page: page.value })}`;
    const data = await api.get<any>(url);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 50;
  } finally {
    loading.value = false;
  }
}

function switchTab(value: 'audit' | 'login') {
  tab.value = value;
  page.value = 1;
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">系统日志</h1>
      <div class="flex gap-2 text-sm">
        <button :class="tab === 'audit' ? 'font-semibold text-[var(--pv-accent)]' : 'muted'" @click="switchTab('audit')">操作日志</button>
        <button :class="tab === 'login' ? 'font-semibold text-[var(--pv-accent)]' : 'muted'" @click="switchTab('login')">登录日志</button>
      </div>
    </div>

    <div v-if="tab === 'audit'" class="surface flex items-center gap-2 p-3">
      <input v-model="keyword" class="input !w-64" placeholder="搜索操作或操作人" @keyup.enter="page = 1; load()" />
      <button class="btn-ghost" @click="page = 1; load()">查询</button>
      <span class="ml-auto text-xs muted">共 {{ total }} 条</span>
    </div>

    <div class="surface overflow-x-auto">
      <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
      <table v-else-if="tab === 'audit'" class="table-base">
        <thead>
          <tr>
            <th class="w-16">ID</th><th class="w-28">操作人</th><th class="w-48">操作</th><th class="w-32">对象</th>
            <th>详情</th><th class="w-32">IP</th><th class="w-32">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="text-xs muted">{{ item.id }}</td>
            <td class="text-xs">{{ item.actor }}</td>
            <td class="font-mono text-xs">{{ item.action }}</td>
            <td class="text-xs muted">{{ item.targetType }}{{ item.targetId ? ` #${item.targetId}` : '' }}</td>
            <td class="text-xs muted">{{ item.detail }}</td>
            <td class="text-xs muted">{{ item.ip }}</td>
            <td class="text-xs muted">{{ fromNow(item.createdAt) }}</td>
          </tr>
        </tbody>
      </table>
      <table v-else class="table-base">
        <thead>
          <tr>
            <th class="w-16">ID</th><th class="w-32">用户名</th><th class="w-32">IP</th>
            <th>User-Agent</th><th class="w-20">结果</th><th class="w-32">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="text-xs muted">{{ item.id }}</td>
            <td class="text-xs">{{ item.username }}</td>
            <td class="text-xs muted">{{ item.ip }}</td>
            <td class="truncate text-xs muted">{{ item.userAgent }}</td>
            <td class="text-xs" :class="item.success ? 'text-emerald-600' : 'text-rose-500'">{{ item.success ? '成功' : '失败' }}</td>
            <td class="text-xs muted">{{ fromNow(item.createdAt) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </div>
</template>
