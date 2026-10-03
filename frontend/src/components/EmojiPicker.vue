<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import Icon from './Icon.vue';

const emit = defineEmits<{ (event: 'pick', value: string): void }>();
const store = useAppStore();
const tab = ref<'mine' | 'popular'>('mine');
const mine = ref<any[]>([]);
const popular = ref<any[]>([]);
const loading = ref(false);
const uploading = ref(false);

async function load() {
  if (!store.isLogin) return;
  loading.value = true;
  try {
    if (tab.value === 'mine') {
      const data = await api.get<any>('/api/emojis');
      mine.value = data.items || [];
    } else {
      const data = await api.get<any>('/api/emojis/popular');
      popular.value = data.items || [];
    }
  } catch {
    /* 忽略：没登录或功能关闭 */
  } finally {
    loading.value = false;
  }
}

async function pick(item: any) {
  // 用 [emoji:地址] 这种标记存进文本，渲染时再还原成图片
  emit('pick', `[emoji:${item.url}]`);
  void api.post(`/api/emojis/${item.id}/use`).catch(() => undefined);
}

async function collect(item: any) {
  try {
    await api.post(`/api/emojis/${item.id}/collect`);
    toast.success('已收藏到我的表情');
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '收藏失败');
  }
}

async function upload(file: File) {
  uploading.value = true;
  try {
    const saved = await api.upload<{ url: string }>('/api/upload/image', file);
    await api.post('/api/emojis', { url: saved.url, name: file.name.replace(/\.[^.]+$/, '').slice(0, 16) });
    toast.success('表情已添加');
    tab.value = 'mine';
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '上传失败');
  } finally {
    uploading.value = false;
  }
}

async function remove(item: any) {
  try {
    await api.del(`/api/emojis/${item.id}`);
    mine.value = mine.value.filter((row) => row.id !== item.id);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  }
}

function switchTab(value: 'mine' | 'popular') {
  tab.value = value;
  void load();
}

void load();
</script>

<template>
  <div class="w-72 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-2 shadow-lg">
    <p v-if="!store.isLogin" class="px-2 py-6 text-center text-xs muted">登录后可以使用表情包</p>
    <template v-else>
      <div class="mb-2 flex items-center gap-1">
        <button
          class="rounded-full px-2.5 py-1 text-xs"
          :class="tab === 'mine' ? 'bg-[var(--pv-surface-2)] font-medium' : 'muted'"
          @click="switchTab('mine')"
        >
          我的
        </button>
        <button
          class="rounded-full px-2.5 py-1 text-xs"
          :class="tab === 'popular' ? 'bg-[var(--pv-surface-2)] font-medium' : 'muted'"
          @click="switchTab('popular')"
        >
          热门
        </button>
        <label class="ml-auto cursor-pointer text-xs text-[var(--pv-accent)] hover:underline">
          {{ uploading ? '上传中…' : '+ 上传' }}
          <input
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            class="hidden"
            @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) upload(file); }"
          />
        </label>
      </div>

      <p v-if="loading" class="py-6 text-center text-xs muted">加载中…</p>
      <template v-else>
        <div class="grid max-h-56 grid-cols-4 gap-1 overflow-y-auto">
          <button
            v-for="item in tab === 'mine' ? mine : popular"
            :key="item.id"
            class="group relative aspect-square rounded-xl p-1 hover:bg-[var(--pv-surface-2)]"
            :title="item.name || ''"
            @click="pick(item)"
          >
            <img :src="item.url" class="h-full w-full object-contain" alt="" />
            <span
              v-if="tab === 'mine'"
              class="absolute right-0 top-0 hidden text-[10px] text-rose-500 group-hover:block"
              @click.stop="remove(item)"
            >
              ✕
            </span>
            <span
              v-else-if="!item.isMine"
              class="absolute right-0 top-0 hidden text-[10px] text-[var(--pv-accent)] group-hover:block"
              title="收藏为我的表情"
              @click.stop="collect(item)"
            >
              ＋
            </span>
          </button>
        </div>
        <p v-if="!(tab === 'mine' ? mine : popular).length" class="py-6 text-center text-xs muted">
          {{ tab === 'mine' ? '还没有表情，点右上角上传一个' : '暂时没有热门表情' }}
        </p>
      </template>
    </template>
  </div>
</template>
