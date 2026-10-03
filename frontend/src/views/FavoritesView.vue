<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';

const store = useAppStore();
const folders = ref<any[]>([]);
const active = ref(0);
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(24);
const loading = ref(true);
const creating = ref(false);
const newFolder = ref({ name: '', description: '', is_public: true });
const watching = ref<any[]>([]);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(
      `/api/users/${store.user?.username}/favorites${query({ folder: active.value || undefined, page: page.value })}`,
    );
    folders.value = data.folders || [];
    active.value = data.activeFolder || 0;
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 24;
    const later = await api.get<any>('/api/me/watch-later');
    watching.value = later.items || [];
  } finally {
    loading.value = false;
  }
}

async function createFolder() {
  if (!newFolder.value.name.trim()) return toast.error('请填写名称');
  await api.post('/api/me/favorite-folders', newFolder.value);
  newFolder.value = { name: '', description: '', is_public: true };
  creating.value = false;
  toast.success('收藏夹已创建');
  void load();
}

async function removeFolder(folder: any) {
  if (!window.confirm(`确定删除收藏夹「${folder.name}」吗？`)) return;
  try {
    await api.del(`/api/me/favorite-folders/${folder.id}`);
    toast.success('已删除');
    active.value = 0;
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
      <h1 class="text-base font-semibold">我的收藏</h1>
      <button class="btn-ghost text-xs" @click="creating = !creating">新建收藏夹</button>
    </div>

    <div v-if="creating" class="card space-y-2 p-4">
      <input v-model="newFolder.name" class="input" placeholder="收藏夹名称" />
      <input v-model="newFolder.description" class="input" placeholder="简介（可选）" />
      <label class="flex items-center gap-2 text-sm text-slate-500">
        <input v-model="newFolder.is_public" type="checkbox" />公开可见
      </label>
      <div class="flex justify-end gap-2">
        <button class="btn-ghost" @click="creating = false">取消</button>
        <button class="btn-primary" @click="createFolder">创建</button>
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="folder in folders"
        :key="folder.id"
        class="group flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm"
        :class="active === folder.id ? 'border-primary bg-primary/10 text-primary' : 'border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'"
        @click="active = folder.id; page = 1; load()"
      >
        {{ folder.name }}
        <span class="text-xs text-slate-400">{{ folder.count }}</span>
        <span v-if="!folder.isDefault" class="hidden text-xs text-rose-500 group-hover:inline" @click.stop="removeFolder(folder)">删除</span>
      </button>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm text-slate-400">加载中…</p>
    <p v-else-if="!items.length" class="card p-16 text-center text-sm text-slate-400">这个收藏夹还是空的</p>
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <VideoCard v-for="video in items" :key="video.id" :video="video" />
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />

    <section v-if="watching.length" class="pt-4">
      <h2 class="mb-3 text-sm font-semibold">稍后再看</h2>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in watching" :key="video.id" :video="video" />
      </div>
    </section>
  </div>
</template>
