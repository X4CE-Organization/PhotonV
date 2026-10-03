<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';
import { fromNow } from '../../utils';

const items = ref<any[]>([]);
const editing = ref<any>(null);
const form = ref({ title: '', content: '', type: 'notice', isPinned: false, isPublic: true });

async function load() {
  const data = await api.get<any>('/api/admin/announcements');
  items.value = data.items || [];
}

function openCreate() {
  editing.value = { id: 0 };
  form.value = { title: '', content: '', type: 'notice', isPinned: false, isPublic: true };
}

function openEdit(item: any) {
  editing.value = item;
  form.value = { title: item.title, content: item.content, type: item.type, isPinned: item.isPinned, isPublic: item.isPublic };
}

async function save() {
  try {
    if (editing.value.id) await api.put(`/api/admin/announcements/${editing.value.id}`, form.value);
    else await api.post('/api/admin/announcements', form.value);
    toast.success('已保存');
    editing.value = null;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function remove(item: any) {
  if (!window.confirm('确定删除该公告吗？')) return;
  await api.del(`/api/admin/announcements/${item.id}`);
  toast.success('已删除');
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-base font-semibold">公告管理</h1>
      <button class="btn-primary text-xs" @click="openCreate">新建公告</button>
    </div>

    <div class="card divide-y divide-slate-100 dark:divide-slate-800">
      <div v-for="item in items" :key="item.id" class="p-4">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="text-sm font-medium">{{ item.title }}</h3>
          <span v-if="item.isPinned" class="rounded bg-rose-100 px-1 text-[10px] text-rose-600 dark:bg-rose-500/20">置顶</span>
          <span v-if="!item.isPublic" class="text-[11px] text-amber-500">未公开</span>
          <span class="ml-auto text-[11px] text-slate-400">{{ fromNow(item.createdAt) }}</span>
        </div>
        <p class="mt-1 line-clamp-2 text-xs text-slate-500">{{ item.content }}</p>
        <div class="mt-2 flex gap-3 text-xs">
          <button class="text-primary hover:underline" @click="openEdit(item)">编辑</button>
          <button class="text-rose-500 hover:underline" @click="remove(item)">删除</button>
        </div>
      </div>
      <p v-if="!items.length" class="p-10 text-center text-sm text-slate-400">还没有公告</p>
    </div>

    <div v-if="editing" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="editing = null">
      <div class="w-full max-w-lg space-y-3 rounded-xl bg-white p-5 dark:bg-slate-900">
        <h2 class="text-sm font-semibold">{{ editing.id ? '编辑公告' : '新建公告' }}</h2>
        <div><label class="label">标题</label><input v-model="form.title" class="input" /></div>
        <div><label class="label">内容</label><textarea v-model="form.content" class="input min-h-[120px]"></textarea></div>
        <div>
          <label class="label">类型</label>
          <select v-model="form.type" class="input">
            <option value="notice">公告</option>
            <option value="update">更新</option>
            <option value="important">重要</option>
          </select>
        </div>
        <div class="flex gap-4 text-sm">
          <label class="flex items-center gap-2"><input v-model="form.isPinned" type="checkbox" />置顶</label>
          <label class="flex items-center gap-2"><input v-model="form.isPublic" type="checkbox" />公开</label>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editing = null">取消</button>
          <button class="btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
