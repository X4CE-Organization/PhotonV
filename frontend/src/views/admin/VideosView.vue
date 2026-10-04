<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { formatNumber, formatSize, fromNow, initials } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';
import Icon from '../../components/Icon.vue';

const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const status = ref('');
const keyword = ref('');
const includeDeleted = ref(false);
const loading = ref(true);
const rejecting = ref<any>(null);
const reason = ref('');

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(
      `/api/admin/videos${query({ q: keyword.value, status: status.value, include_deleted: includeDeleted.value ? 1 : 0, page: page.value })}`,
    );
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
  } finally {
    loading.value = false;
  }
}

async function review(video: any, approve: boolean, note = '') {
  await api.post(`/api/admin/videos/${video.id}/review`, { approve, reason: note });
  toast.success(approve ? '已通过审核' : '已驳回');
  rejecting.value = null;
  reason.value = '';
  void load();
}

async function update(video: any, payload: Record<string, unknown>) {
  await api.put(`/api/admin/videos/${video.id}`, payload);
  Object.assign(video, payload);
  toast.success('已更新');
}

async function remove(video: any) {
  if (!window.confirm(`确定删除《${video.title}》吗？`)) return;
  await api.del(`/api/admin/videos/${video.id}`);
  toast.success('已删除');
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">视频管理</h1>
      <span class="text-sm muted">共 {{ total }} 个视频</span>
    </div>

    <div class="surface flex flex-wrap items-center gap-2 p-3">
      <input v-model="keyword" class="input !w-56" placeholder="搜索标题 / 简介" @keyup.enter="page = 1; load()" />
      <select v-model="status" class="input !w-32" @change="page = 1; load()">
        <option value="">全部状态</option>
        <option value="pending">待审核</option>
        <option value="published">已公开</option>
        <option value="rejected">已驳回</option>
        <option value="private">私密</option>
      </select>
      <label class="flex items-center gap-1.5 text-sm muted">
        <input v-model="includeDeleted" type="checkbox" @change="page = 1; load()" />包含已删除
      </label>
      <button class="btn-ghost" @click="page = 1; load()">查询</button>
    </div>

    <div class="surface overflow-x-auto">
      <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
      <table v-else class="table-base">
        <thead>
          <tr>
            <th>视频</th>
            <th class="w-28">UP 主</th>
            <th class="w-24">状态</th>
            <th class="w-32">数据</th>
            <th class="w-28">大小</th>
            <th class="w-24">投稿时间</th>
            <th class="w-56">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="video in items" :key="video.id" :class="video.deleted ? 'opacity-50' : ''">
            <td>
              <div class="flex gap-2">
                <img :src="video.cover" class="h-12 w-20 shrink-0 rounded object-cover" alt="" />
                <div class="min-w-0">
                  <RouterLink :to="`/video/${video.id}`" class="line-clamp-2 text-sm hover:text-[var(--pv-accent)]">{{ video.title }}</RouterLink>
                  <p class="mt-0.5 line-clamp-1 text-[11px] muted">{{ video.description }}</p>
                  <span v-if="video.rejectReason" class="text-[11px] text-rose-500">驳回原因：{{ video.rejectReason }}</span>
                </div>
              </div>
            </td>
            <td class="text-xs">
              <div class="flex items-center gap-1.5">
                <img v-if="video.author?.avatar" :src="video.author.avatar" class="h-6 w-6 rounded-full object-cover" alt="" />
                <span v-else class="grid h-6 w-6 place-items-center rounded-full bg-[var(--pv-accent)]/15 text-[10px] text-[var(--pv-accent)]">
                  {{ initials(video.author?.displayName) }}
                </span>
                {{ video.author?.displayName }}
              </div>
            </td>
            <td class="text-xs">
              <span
                class="rounded px-1.5 py-0.5"
                :class="{ 'bg-amber-100 text-amber-700 dark:bg-amber-500/20': video.status === 'pending', 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20': 'published', 'bg-rose-100 text-rose-600 dark:bg-rose-500/20': 'rejected', 'bg-[var(--pv-surface-2)] muted bg-[var(--pv-surface-2)]': 'private', }"
              >
                {{ video.status === 'pending' ? '待审核' : video.status === 'published' ? '已公开' : video.status === 'rejected' ? '已驳回' : '私密' }}
              </span>
              <span v-if="video.deleted" class="mt-1 block text-rose-500">已删除</span>
            </td>
            <td class="text-xs muted">
              <span class="inline-flex items-center gap-1"><Icon name="play" :size="12" />{{ formatNumber(video.views) }}</span>
              <span class="ml-2 inline-flex items-center gap-1"><Icon name="heart" :size="12" />{{ formatNumber(video.likes) }}</span>
              <br />
              <span class="inline-flex items-center gap-1"><Icon name="message" :size="12" />{{ formatNumber(video.comments) }}</span>
              <span class="ml-2 inline-flex items-center gap-1"><Icon name="zap" :size="12" />{{ formatNumber(video.danmaku) }}</span>
            </td>
            <td class="text-xs muted">{{ formatSize(video.filesize) }}</td>
            <td class="text-xs muted">{{ fromNow(video.createdAt) }}</td>
            <td>
              <div class="flex flex-wrap gap-2 text-xs">
                <template v-if="video.status === 'pending'">
                  <button class="text-emerald-600 hover:underline" @click="review(video, true)">通过</button>
                  <button class="text-rose-500 hover:underline" @click="rejecting = video">驳回</button>
                </template>
                <button class="text-[var(--pv-accent)] hover:underline" @click="update(video, { isFeatured: !video.isFeatured })">
                  {{ video.isFeatured ? '取消精选' : '设为精选' }}
                </button>
                <button class="text-[var(--pv-accent)] hover:underline" @click="update(video, { isPinned: !video.isPinned })">
                  {{ video.isPinned ? '取消置顶' : '置顶' }}
                </button>
                <button class="muted hover:underline" @click="update(video, { allowComment: !video.allowComment })">
                  {{ video.allowComment ? '关闭评论' : '开启评论' }}
                </button>
                <button v-if="!video.deleted" class="text-rose-500 hover:underline" @click="remove(video)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />

    <div v-if="rejecting" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="rejecting = null">
      <div class="w-full max-w-md rounded-xl bg-white p-5 bg-[var(--pv-surface-2)]">
        <h2 class="text-sm font-semibold">驳回《{{ rejecting.title }}》</h2>
        <textarea v-model="reason" class="input mt-3 min-h-[90px]" placeholder="填写驳回原因，作者会收到通知"></textarea>
        <div class="mt-3 flex justify-end gap-2">
          <button class="btn-ghost" @click="rejecting = null">取消</button>
          <button class="btn-danger" @click="review(rejecting, false, reason)">确认驳回</button>
        </div>
      </div>
    </div>
  </div>
</template>
