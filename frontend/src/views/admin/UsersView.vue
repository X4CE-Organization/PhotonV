<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { useAppStore } from '../../store';
import { formatNumber, fromNow, initials } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';

const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const keyword = ref('');
const role = ref('');
const banned = ref('');
const loading = ref(true);
const editing = ref<any>(null);
const form = ref<any>({});

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/admin/users${query({ q: keyword.value, role: role.value, banned: banned.value, page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
  } finally {
    loading.value = false;
  }
}

function edit(user: any) {
  editing.value = user;
  form.value = {
    role: user.role,
    isBanned: user.isBanned,
    banReason: user.banReason || '',
    coins: user.coins,
    password: '',
    displayName: user.displayName,
    email: user.email,
  };
}

async function save() {
  try {
    const payload: any = {
      isBanned: form.value.isBanned,
      banReason: form.value.banReason,
      profile: { displayName: form.value.displayName, email: form.value.email },
    };
    if (store.isSuperadmin) {
      payload.role = form.value.role;
      payload.coins = Number(form.value.coins);
      if (form.value.password) payload.password = form.value.password;
    }
    await api.put(`/api/admin/users/${editing.value.id}`, payload);
    toast.success('已保存');
    editing.value = null;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function toggleBan(user: any) {
  const reason = user.isBanned ? '' : window.prompt('封禁原因', '违反社区规范') || '';
  await api.put(`/api/admin/users/${user.id}`, { isBanned: !user.isBanned, banReason: reason });
  toast.success(user.isBanned ? '已解封' : '已封禁');
  void load();
}

async function remove(user: any) {
  if (!window.confirm(`确定删除用户 ${user.username} 及其全部数据吗？`)) return;
  try {
    await api.del(`/api/admin/users/${user.id}`);
    toast.success('已删除');
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">用户管理</h1>
      <span class="text-sm muted">共 {{ total }} 位用户</span>
    </div>

    <div class="surface flex flex-wrap items-center gap-2 p-3">
      <input v-model="keyword" class="input !w-56" placeholder="搜索用户名 / 昵称 / 邮箱" @keyup.enter="page = 1; load()" />
      <select v-model="role" class="input !w-32" @change="page = 1; load()">
        <option value="">全部角色</option>
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
        <option value="superadmin">超级管理员</option>
      </select>
      <select v-model="banned" class="input !w-32" @change="page = 1; load()">
        <option value="">全部状态</option>
        <option value="false">正常</option>
        <option value="true">已封禁</option>
      </select>
      <button class="btn-ghost" @click="page = 1; load()">查询</button>
    </div>

    <div class="surface overflow-x-auto">
      <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
      <table v-else class="table-base">
        <thead>
          <tr>
            <th class="w-14">ID</th>
            <th>用户</th>
            <th class="w-24">角色</th>
            <th class="w-20">硬币</th>
            <th class="w-20">投稿</th>
            <th class="w-24">粉丝</th>
            <th class="w-32">最近登录</th>
            <th class="w-40">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in items" :key="user.id" :class="user.isBanned ? 'opacity-60' : ''">
            <td class="text-xs muted">{{ user.id }}</td>
            <td>
              <div class="flex items-center gap-2">
                <img v-if="user.avatar" :src="user.avatar" class="h-8 w-8 rounded-full object-cover" alt="" />
                <span v-else class="grid h-8 w-8 place-items-center rounded-full bg-[var(--pv-accent)]/15 text-xs font-semibold text-[var(--pv-accent)]">
                  {{ initials(user.displayName) }}
                </span>
                <div>
                  <span class="text-sm">{{ user.displayName }}</span>
                  <span v-if="user.isBanned" class="ml-2 rounded bg-rose-100 px-1 text-[10px] text-rose-600 dark:bg-rose-500/20">已封禁</span>
                  <div class="font-mono text-[11px] muted">@{{ user.username }}</div>
                  <div class="text-[11px] muted">{{ user.email || '未填写邮箱' }}</div>
                </div>
              </div>
            </td>
            <td class="text-xs">{{ user.role === 'superadmin' ? '超级管理员' : user.role === 'admin' ? '管理员' : '普通用户' }}</td>
            <td class="text-[var(--pv-accent)]">{{ user.coins }}</td>
            <td>{{ user.videoCount }}</td>
            <td>{{ formatNumber(user.followerCount) }}</td>
            <td class="text-xs muted">
              {{ user.lastLoginAt ? fromNow(user.lastLoginAt) : '从未' }}
              <div class="text-[11px]">{{ user.lastLoginIp }}</div>
            </td>
            <td>
              <div class="flex flex-wrap gap-2 text-xs">
                <button class="text-[var(--pv-accent)] hover:underline" @click="edit(user)">编辑</button>
                <button :class="user.isBanned ? 'text-emerald-600' : 'text-amber-600'" class="hover:underline" @click="toggleBan(user)">
                  {{ user.isBanned ? '解封' : '封禁' }}
                </button>
                <button v-if="store.isSuperadmin && user.role !== 'superadmin'" class="text-rose-500 hover:underline" @click="remove(user)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />

    <div v-if="editing" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="editing = null">
      <div class="w-full max-w-md space-y-3 rounded-xl bg-white p-5 bg-[var(--pv-surface-2)]">
        <h2 class="text-sm font-semibold">编辑用户：{{ editing.username }}</h2>
        <div><label class="label">昵称</label><input v-model="form.displayName" class="input" /></div>
        <div><label class="label">邮箱</label><input v-model="form.email" class="input" /></div>
        <div v-if="store.isSuperadmin">
          <label class="label">角色</label>
          <select v-model="form.role" class="input">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
            <option value="superadmin">超级管理员</option>
          </select>
        </div>
        <div v-if="store.isSuperadmin"><label class="label">硬币</label><input v-model="form.coins" type="number" class="input" /></div>
        <div v-if="store.isSuperadmin"><label class="label">重置密码（留空不改）</label><input v-model="form.password" class="input" /></div>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.isBanned" type="checkbox" />封禁该用户</label>
        <input v-if="form.isBanned" v-model="form.banReason" class="input" placeholder="封禁原因" />
        <div class="flex justify-end gap-2 pt-1">
          <button class="btn-ghost" @click="editing = null">取消</button>
          <button class="btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
