<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { formatNumber, fromNow, initials } from '../../utils';
import Icon from '../../components/Icon.vue';

const items = ref<any[]>([]);
const status = ref('');
const loading = ref(true);
const permissionName = ref('');

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/live/admin/rooms${query({ status: status.value })}`);
    items.value = data.items || [];
  } finally {
    loading.value = false;
  }
}

async function setStatus(room: any, next: string) {
  await api.post(`/api/live/admin/rooms/${room.id}/status`, { status: next });
  toast.success('已更新直播间状态');
  void load();
}

async function remove(room: any) {
  if (!window.confirm(`确定删除直播间「${room.title}」吗？`)) return;
  await api.del(`/api/live/rooms/${room.id}`);
  toast.success('已删除');
  void load();
}

async function grantPermission() {
  const name = permissionName.value.trim();
  if (!name) return toast.error('请输入用户名');
  try {
    const user = await api.get<any>(`/api/users/${encodeURIComponent(name)}`);
    await api.post(`/api/admin/users/${user.profile.id}/live-permission`, { canLive: true });
    toast.success(`已为 ${name} 开通直播权限`);
    permissionName.value = '';
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">直播管理</h1>
      <select v-model="status" class="input !w-32" @change="load">
        <option value="">全部状态</option>
        <option value="live">直播中</option>
        <option value="offline">未开播</option>
        <option value="banned">已封禁</option>
      </select>
    </div>

    <div class="surface flex flex-wrap items-center gap-2 p-3">
      <input v-model="permissionName" class="input !w-56" placeholder="输入用户名，为其开通直播权限" />
      <button class="btn-primary text-xs" @click="grantPermission">
        <Icon name="key" :size="15" />开通直播权限
      </button>
      <span class="text-xs muted">默认需要管理员开通后用户才能创建直播间</span>
    </div>

    <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
    <div v-else class="surface overflow-x-auto">
      <table class="table-base">
        <thead>
          <tr>
            <th>直播间</th><th class="w-32">主播</th><th class="w-24">状态</th>
            <th class="w-28">人气</th><th class="w-28">聊天</th><th class="w-32">开播时间</th><th class="w-56">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="room in items" :key="room.id">
            <td>
              <div class="flex items-center gap-2">
                <img v-if="room.cover" :src="room.cover" class="h-10 w-16 rounded-lg object-cover" alt="" />
                <div class="min-w-0">
                  <div class="text-sm">{{ room.title }}</div>
                  <div class="line-clamp-1 text-[11px] muted">{{ room.description }}</div>
                </div>
              </div>
            </td>
            <td class="text-xs">
              <div class="flex items-center gap-1.5">
                <img v-if="room.owner?.avatar" :src="room.owner.avatar" class="h-6 w-6 rounded-full object-cover" alt="" />
                <span v-else class="grid h-6 w-6 place-items-center rounded-full bg-[var(--pv-surface-2)] text-[10px] font-bold">
                  {{ initials(room.owner?.displayName) }}
                </span>
                {{ room.owner?.displayName }}
              </div>
            </td>
            <td class="text-xs">
              <span :class="room.status === 'live' ? 'text-rose-500' : room.status === 'banned' ? 'text-amber-500' : 'muted'">
                {{ room.status === 'live' ? '直播中' : room.status === 'banned' ? '已封禁' : '未开播' }}
              </span>
            </td>
            <td class="text-xs">{{ formatNumber(room.viewers) }} / 累计 {{ formatNumber(room.totalViewers) }}</td>
            <td class="text-xs">{{ formatNumber(room.chatCount) }}</td>
            <td class="text-xs muted">{{ room.startedAt ? fromNow(room.startedAt) : '—' }}</td>
            <td>
              <div class="flex flex-wrap gap-2 text-xs">
                <button v-if="room.status !== 'live'" class="text-emerald-500 hover:underline" @click="setStatus(room, 'live')">允许开播</button>
                <button v-else class="muted hover:underline" @click="setStatus(room, 'offline')">强制下播</button>
                <button v-if="room.status !== 'banned'" class="text-amber-500 hover:underline" @click="setStatus(room, 'banned')">封禁</button>
                <button class="text-rose-500 hover:underline" @click="remove(room)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!items.length" class="p-10 text-center text-sm muted">还没有直播间</p>
    </div>
  </div>
</template>
