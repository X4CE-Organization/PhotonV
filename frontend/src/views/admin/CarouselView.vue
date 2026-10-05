<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';

const items = ref<any[]>([]);
const editing = ref<any>(null);
const form = ref({ title: '', subtitle: '', image: '', link: '', sort: 0, isActive: true });

async function load() {
  const data = await api.get<any>('/api/admin/carousel');
  items.value = data.items || [];
}

function openCreate() {
  editing.value = { id: 0 };
  form.value = { title: '', subtitle: '', image: '', link: '', sort: items.value.length, isActive: true };
}

function openEdit(item: any) {
  editing.value = item;
  form.value = { ...item };
}

async function upload(file: File) {
  const result = await api.upload<{ url: string }>('/api/upload/image', file);
  form.value.image = result.url;
  toast.success('图片已上传');
}

async function save() {
  try {
    if (editing.value.id) await api.put(`/api/admin/carousel/${editing.value.id}`, form.value);
    else await api.post('/api/admin/carousel', form.value);
    toast.success('已保存');
    editing.value = null;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function remove(item: any) {
  if (!window.confirm('确定删除该轮播吗？')) return;
  await api.del(`/api/admin/carousel/${item.id}`);
  toast.success('已删除');
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-base font-semibold">首页轮播</h1>
      <button class="btn-primary text-xs" @click="openCreate">新增轮播</button>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <div v-for="item in items" :key="item.id" class="surface overflow-hidden">
        <img :src="item.image" class="aspect-[16/7] w-full object-cover" alt="" />
        <div class="p-3">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-medium">{{ item.title || '未命名' }}</h3>
            <span v-if="!item.isActive" class="text-[11px] text-amber-500">已停用</span>
          </div>
          <p class="mt-1 text-xs muted">{{ item.subtitle }}</p>
          <div class="mt-2 flex gap-3 text-xs">
            <button class="text-[var(--pv-accent)] hover:underline" @click="openEdit(item)">编辑</button>
            <button class="text-rose-500 hover:underline" @click="remove(item)">删除</button>
          </div>
        </div>
      </div>
      <p v-if="!items.length" class="surface col-span-full p-10 text-center text-sm muted">还没有轮播图</p>
    </div>

    <div v-if="editing" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="editing = null">
      <div class="w-full max-w-md space-y-3 rounded-xl bg-white p-5 bg-[var(--pv-surface-2)]">
        <h2 class="text-sm font-semibold">{{ editing.id ? '编辑轮播' : '新增轮播' }}</h2>
        <div><label class="label">标题</label><input v-model="form.title" class="input" /></div>
        <div><label class="label">副标题</label><input v-model="form.subtitle" class="input" /></div>
        <div>
          <label class="label">图片</label>
          <div class="flex items-center gap-3">
            <img v-if="form.image" :src="form.image" class="h-14 w-28 rounded object-cover" alt="" />
            <label class="btn-ghost cursor-pointer">
              上传图片
              <input
                type="file"
                accept="image/*"
                class="hidden"
                @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) upload(file); }"
              />
            </label>
          </div>
        </div>
        <div><label class="label">跳转链接</label><input v-model="form.link" class="input" placeholder="/video/1 或外链" /></div>
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
