<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';

const categories = ref<any[]>([]);
const tags = ref<any[]>([]);
const editing = ref<any>(null);
const form = ref({ name: '', slug: '', icon: '🎬', description: '', sort: 0, isActive: true });

async function load() {
  const [categoryData, tagData] = await Promise.all([
    api.get<any>('/api/admin/categories'),
    api.get<any>('/api/admin/tags'),
  ]);
  categories.value = categoryData.items || [];
  tags.value = tagData.items || [];
}

function openCreate() {
  editing.value = { id: 0 };
  form.value = { name: '', slug: '', icon: '🎬', description: '', sort: categories.value.length, isActive: true };
}

function openEdit(item: any) {
  editing.value = item;
  form.value = {
    name: item.name,
    slug: item.slug,
    icon: item.icon,
    description: item.description,
    sort: item.sort,
    isActive: item.isActive,
  };
}

async function save() {
  try {
    if (editing.value.id) {
      await api.put(`/api/admin/categories/${editing.value.id}`, form.value);
    } else {
      await api.post('/api/admin/categories', form.value);
    }
    toast.success('已保存');
    editing.value = null;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function remove(item: any) {
  if (!window.confirm(`确定删除分区「${item.name}」吗？该分区下的视频会变成未分区。`)) return;
  await api.del(`/api/admin/categories/${item.id}`);
  toast.success('已删除');
  void load();
}

async function removeTag(item: any) {
  if (!window.confirm(`确定删除标签「${item.name}」吗？`)) return;
  await api.del(`/api/admin/tags/${item.id}`);
  toast.success('已删除');
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-base font-semibold">分区与标签</h1>
      <button class="btn-primary text-xs" @click="openCreate">新建分区</button>
    </div>

    <div class="card overflow-x-auto">
      <table class="table-base">
        <thead>
          <tr>
            <th class="w-16">图标</th><th>名称</th><th class="w-28">标识</th><th class="w-64">描述</th>
            <th class="w-16">排序</th><th class="w-20">视频数</th><th class="w-20">状态</th><th class="w-28">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in categories" :key="item.id">
            <td class="text-lg">{{ item.icon }}</td>
            <td>{{ item.name }}</td>
            <td class="font-mono text-xs text-slate-400">{{ item.slug }}</td>
            <td class="text-xs text-slate-500">{{ item.description }}</td>
            <td class="text-xs">{{ item.sort }}</td>
            <td class="text-xs">{{ item.count }}</td>
            <td class="text-xs">
              <span :class="item.isActive ? 'text-emerald-600' : 'text-slate-400'">{{ item.isActive ? '启用' : '停用' }}</span>
            </td>
            <td class="text-xs">
              <button class="text-primary hover:underline" @click="openEdit(item)">编辑</button>
              <button class="ml-2 text-rose-500 hover:underline" @click="remove(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <section class="card p-4">
      <h2 class="text-sm font-semibold">标签（{{ tags.length }}）</h2>
      <div class="mt-3 flex flex-wrap gap-2">
        <span
          v-for="item in tags"
          :key="item.id"
          class="group flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs dark:bg-slate-800"
        >
          {{ item.name }} <span class="text-slate-400">{{ item.useCount }}</span>
          <button class="hidden text-rose-500 group-hover:inline" @click="removeTag(item)">×</button>
        </span>
        <span v-if="!tags.length" class="text-xs text-slate-400">还没有标签</span>
      </div>
    </section>

    <div v-if="editing" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="editing = null">
      <div class="w-full max-w-md space-y-3 rounded-xl bg-white p-5 dark:bg-slate-900">
        <h2 class="text-sm font-semibold">{{ editing.id ? '编辑分区' : '新建分区' }}</h2>
        <div><label class="label">名称</label><input v-model="form.name" class="input" /></div>
        <div><label class="label">标识（用于地址，留空自动生成）</label><input v-model="form.slug" class="input" /></div>
        <div><label class="label">图标（emoji）</label><input v-model="form.icon" class="input" /></div>
        <div><label class="label">描述</label><input v-model="form.description" class="input" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">排序</label><input v-model.number="form.sort" type="number" class="input" /></div>
          <label class="mt-6 flex items-center gap-2 text-sm"><input v-model="form.isActive" type="checkbox" />启用</label>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editing = null">取消</button>
          <button class="btn-primary" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
