<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { fromNow } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';

const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const status = ref('pending');
const loading = ref(true);
const handling = ref<any>(null);
const note = ref('');

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/admin/reports${query({ status: status.value, page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
  } finally {
    loading.value = false;
  }
}

async function handle(action: string) {
  await api.post(`/api/admin/reports/${handling.value.id}/handle`, { action, note: note.value });
  toast.success('已处理');
  handling.value = null;
  note.value = '';
  void load();
}

function targetLink(item: any): string {
  if (item.targetType === 'video') return `/video/${item.targetId}`;
  if (item.targetType === 'user') return `/space/${item.targetTitle}`;
  return '#';
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">举报处理</h1>
      <select v-model="status" class="input !w-32" @change="page = 1; load()">
        <option value="pending">待处理</option>
        <option value="handled">已处理</option>
        <option value="rejected">已驳回</option>
        <option value="">全部</option>
      </select>
    </div>

    <div class="surface overflow-x-auto">
      <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
      <table v-else class="table-base">
        <thead>
          <tr>
            <th class="w-20">类型</th><th>被举报内容</th><th class="w-24">理由</th><th class="w-40">补充说明</th>
            <th class="w-28">举报人</th><th class="w-24">时间</th><th class="w-32">状态</th><th class="w-20">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="text-xs">
              {{ item.targetType === 'video' ? '视频' : item.targetType === 'comment' ? '评论' : item.targetType === 'danmaku' ? '弹幕' : '用户' }}
            </td>
            <td>
              <RouterLink :to="targetLink(item)" class="text-sm hover:text-[var(--pv-accent)]">{{ item.targetTitle || `#${item.targetId}` }}</RouterLink>
            </td>
            <td class="text-xs">{{ item.reason }}</td>
            <td class="text-xs muted">{{ item.detail || '—' }}</td>
            <td class="text-xs">{{ item.reporter?.displayName }}</td>
            <td class="text-xs muted">{{ fromNow(item.createdAt) }}</td>
            <td class="text-xs">
              <span :class="item.status === 'pending' ? 'text-amber-600' : item.status === 'handled' ? 'text-emerald-600' : 'muted'">
                {{ item.status === 'pending' ? '待处理' : item.status === 'handled' ? '已处理' : '已驳回' }}
              </span>
              <div v-if="item.handleNote" class="text-[11px] muted">{{ item.handleNote }}</div>
            </td>
            <td>
              <button v-if="item.status === 'pending'" class="text-xs text-[var(--pv-accent)] hover:underline" @click="handling = item">处理</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />

    <div v-if="handling" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="handling = null">
      <div class="w-full max-w-md space-y-3 rounded-xl bg-white p-5 bg-[var(--pv-surface-2)]">
        <h2 class="text-sm font-semibold">处理举报</h2>
        <p class="text-xs muted">被举报对象：{{ handling.targetTitle }}（{{ handling.reason }}）</p>
        <textarea v-model="note" class="input min-h-[80px]" placeholder="处理说明（会通知举报人）"></textarea>
        <div class="flex flex-wrap justify-end gap-2">
          <button class="btn-ghost" @click="handle('reject')">驳回举报</button>
          <button class="btn-primary" @click="handle('handled')">仅标记已处理</button>
          <button class="btn-danger" @click="handle('delete')">删除内容并处理</button>
        </div>
      </div>
    </div>
  </div>
</template>
