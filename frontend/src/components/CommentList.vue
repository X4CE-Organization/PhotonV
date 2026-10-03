<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { fromNow, initials } from '../utils';
import Icon from './Icon.vue';
import PaginationBar from './PaginationBar.vue';

const props = defineProps<{ videoId: number; allowComment: boolean }>();
const store = useAppStore();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(20);
const sort = ref(String(store.settings.comment_order || 'hot'));
const draft = ref('');
const replyTo = ref<any>(null);
const sending = ref(false);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/videos/${props.videoId}/comments${query({ page: page.value, sort: sort.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 20;
  } finally {
    loading.value = false;
  }
}

async function submit() {
  const content = draft.value.trim();
  if (!content) return;
  if (!store.isLogin) {
    toast.info('登录后才能评论');
    return;
  }
  sending.value = true;
  try {
    await api.post(`/api/videos/${props.videoId}/comments`, {
      content,
      parent_id: replyTo.value?.id || null,
    });
    draft.value = '';
    replyTo.value = null;
    await load();
    toast.success('评论成功');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '评论失败');
  } finally {
    sending.value = false;
  }
}

async function like(item: any) {
  if (!store.isLogin) return toast.info('登录后才能点赞');
  const data = await api.post<any>(`/api/comments/${item.id}/like`);
  item.liked = data.liked;
  item.likeCount = data.likeCount;
}

async function remove(item: any) {
  if (!window.confirm('确定删除这条评论吗？')) return;
  await api.del(`/api/comments/${item.id}`);
  toast.success('已删除');
  await load();
}

async function pin(item: any) {
  const data = await api.post<any>(`/api/comments/${item.id}/pin`);
  item.isPinned = data.isPinned;
  toast.success(data.isPinned ? '已置顶' : '已取消置顶');
}

watch(() => props.videoId, () => {
  page.value = 1;
  void load();
});

function changeSort(value: string) {
  sort.value = value;
  page.value = 1;
  void load();
}

onMounted(load);
</script>

<template>
  <section class="card mt-4 p-4">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold">评论 {{ total }}</h2>
      <div class="flex gap-2 text-xs">
        <button :class="sort === 'hot' ? 'text-primary' : 'text-slate-400'" @click="changeSort('hot')">最热</button>
        <button :class="sort === 'new' ? 'text-primary' : 'text-slate-400'" @click="changeSort('new')">最新</button>
      </div>
    </div>

    <div v-if="allowComment" class="mb-4">
      <div v-if="replyTo" class="mb-1 text-xs text-slate-500">
        回复 @{{ replyTo.author?.displayName }}
        <button class="ml-2 text-primary" @click="replyTo = null">取消</button>
      </div>
      <div class="flex items-start gap-2">
        <textarea
          v-model="draft"
          class="input min-h-[70px] flex-1"
          :placeholder="store.isLogin ? '发一条友善的评论' : '登录后参与评论'"
          :disabled="!store.isLogin"
        ></textarea>
        <button class="btn-primary" :disabled="sending || !draft.trim()" @click="submit">发布</button>
      </div>
    </div>
    <p v-else class="mb-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-500 dark:bg-slate-800/60">UP 主已关闭该视频的评论。</p>

    <p v-if="loading" class="py-6 text-center text-sm text-slate-400">加载评论中…</p>
    <p v-else-if="!items.length" class="py-6 text-center text-sm text-slate-400">还没有评论，来抢沙发～</p>

    <ul v-else class="space-y-4">
      <li v-for="item in items" :key="item.id" class="flex gap-3">
        <RouterLink :to="`/space/${item.author?.username}`" class="shrink-0">
          <img v-if="item.author?.avatar" :src="item.author.avatar" class="h-9 w-9 rounded-full object-cover" alt="" />
          <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
            {{ initials(item.author?.displayName) }}
          </span>
        </RouterLink>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <RouterLink :to="`/space/${item.author?.username}`" class="font-medium text-slate-600 hover:text-primary dark:text-slate-300">
              {{ item.author?.displayName }}
            </RouterLink>
            <span v-if="item.isPinned" class="rounded bg-primary/10 px-1 text-primary">置顶</span>
            <span>{{ fromNow(item.createdAt) }}</span>
          </div>
          <p class="mt-1 whitespace-pre-wrap break-words text-sm">{{ item.content }}</p>
          <div class="mt-1 flex items-center gap-3 text-xs text-slate-400">
            <button class="inline-flex items-center gap-1" :class="item.liked ? 'text-rose-500' : 'hover:text-rose-500'" @click="like(item)">
              <Icon name="heart" :size="13" />{{ item.likeCount }}
            </button>
            <button v-if="allowComment" class="hover:text-primary" @click="replyTo = item">回复</button>
            <button v-if="item.canDelete" class="hover:text-primary" @click="pin(item)">{{ item.isPinned ? '取消置顶' : '置顶' }}</button>
            <button v-if="item.canDelete" class="hover:text-rose-500" @click="remove(item)">删除</button>
          </div>

          <ul v-if="item.replies?.length" class="mt-2 space-y-2 border-l-2 border-slate-100 pl-3 dark:border-slate-800">
            <li v-for="reply in item.replies" :key="reply.id" class="text-sm">
              <span class="text-xs text-primary">{{ reply.author?.displayName }}</span>
              <span class="ml-2 text-slate-600 dark:text-slate-300">{{ reply.content }}</span>
              <span class="ml-2 text-xs text-slate-400">{{ fromNow(reply.createdAt) }}</span>
            </li>
          </ul>
          <p v-if="item.replyCount > (item.replies?.length || 0)" class="mt-1 text-xs text-slate-400">
            共 {{ item.replyCount }} 条回复
          </p>
        </div>
      </li>
    </ul>

    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </section>
</template>
