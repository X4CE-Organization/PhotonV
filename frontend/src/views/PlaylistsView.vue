<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import Icon from '../components/Icon.vue';
import { formatNumber } from '../utils';

const items = ref<any[]>([]);
const loading = ref(true);
const creating = ref(false);
const editing = ref<any>(null);
const form = ref({ title: '', description: '', is_public: true });

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>('/api/playlists/mine');
    items.value = data.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { title: '', description: '', is_public: true };
  creating.value = true;
}

function openEdit(item: any) {
  editing.value = item;
  form.value = { title: item.title, description: item.description || '', is_public: item.isPublic };
  creating.value = true;
}

async function submit() {
  if (!form.value.title.trim()) return toast.error('请填写合集标题');
  try {
    if (editing.value) {
      await api.put(`/api/playlists/${editing.value.id}`, form.value);
      toast.success('合集已更新');
    } else {
      await api.post('/api/playlists', form.value);
      toast.success('合集已创建');
    }
    creating.value = false;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

async function remove(item: any) {
  if (!window.confirm(`确定删除合集「${item.title}」吗？合集里的视频不会被删除。`)) return;
  try {
    await api.del(`/api/playlists/${item.id}`);
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
    <div class="flex items-center justify-between">
      <h1 class="flex items-center gap-2 text-base font-semibold"><Icon name="list" :size="18" />我的合集</h1>
      <button class="btn-primary text-xs" @click="openCreate">新建合集</button>
    </div>

    <div v-if="creating" class="surface space-y-2 p-4">
      <input v-model="form.title" class="input" placeholder="合集标题" />
      <textarea v-model="form.description" class="input min-h-[70px]" placeholder="合集简介（可选）" />
      <label class="flex items-center gap-2 text-xs muted">
        <input v-model="form.is_public" type="checkbox" />公开合集（其他人可以看到）
      </label>
      <div class="flex justify-end gap-2">
        <button class="btn-ghost" @click="creating = false">取消</button>
        <button class="btn-primary" @click="submit">{{ editing ? '保存' : '创建' }}</button>
      </div>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm muted">加载中…</p>
    <p v-else-if="!items.length" class="surface p-16 text-center text-sm muted">
      还没有合集，点右上角新建一个，把想连起来看的视频放进去。
    </p>
    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="item in items" :key="item.id" class="surface overflow-hidden">
        <RouterLink :to="`/playlist/${item.id}`" class="block">
          <img v-if="item.cover" :src="item.cover" class="h-32 w-full object-cover" alt="" />
          <div v-else class="grid h-32 w-full place-items-center bg-[var(--pv-surface-2)] text-xs muted">暂无封面</div>
        </RouterLink>
        <div class="space-y-2 p-3">
          <RouterLink :to="`/playlist/${item.id}`" class="line-clamp-1 font-medium hover:text-[var(--pv-accent)]">
            {{ item.title }}
          </RouterLink>
          <p class="line-clamp-2 text-xs muted">{{ item.description || '这个合集还没有简介' }}</p>
          <div class="flex items-center gap-2 text-[11px] muted">
            <span>{{ formatNumber(item.videoCount) }} 个视频</span>
            <span class="chip !py-0 text-[10px]">{{ item.isPublic ? '公开' : '私有' }}</span>
          </div>
          <div class="flex gap-3 pt-1 text-xs">
            <button class="muted hover:text-[var(--pv-accent)]" @click="openEdit(item)">编辑</button>
            <button class="text-rose-500 hover:underline" @click="remove(item)">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
