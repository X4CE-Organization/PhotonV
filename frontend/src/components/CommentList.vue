<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { fromNow, initials, renderRich } from '../utils';
import Icon from './Icon.vue';
import PaginationBar from './PaginationBar.vue';
import EmojiPicker from './EmojiPicker.vue';

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
const showEmoji = ref(false);

function insertEmoji(token: string) {
  draft.value = `${draft.value}${draft.value && !draft.value.endsWith(' ') ? ' ' : ''}${token} `;
  showEmoji.value = false;
}

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
  <section class="surface mt-4 p-4">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold">评论 {{ total }}</h2>
      <div class="flex gap-2 text-xs">
        <button :class="sort === 'hot' ? 'text-[var(--pv-accent)]' : 'muted'" @click="changeSort('hot')">最热</button>
        <button :class="sort === 'new' ? 'text-[var(--pv-accent)]' : 'muted'" @click="changeSort('new')">最新</button>
      </div>
    </div>

    <div v-if="allowComment" class="mb-4">
      <div v-if="replyTo" class="mb-1 text-xs muted">
        回复 @{{ replyTo.author?.displayName }}
        <button class="ml-2 text-[var(--pv-accent)]" @click="replyTo = null">取消</button>
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
      <div class="relative mt-2">
        <button class="btn-ghost text-xs" :disabled="!store.isLogin" @click="showEmoji = !showEmoji">
          <Icon name="sparkles" :size="14" />表情
        </button>
        <div v-if="showEmoji" class="absolute bottom-full left-0 z-30 mb-2">
          <EmojiPicker @pick="insertEmoji" />
        </div>
        <span class="ml-2 text-[11px] muted">输入 @用户名 可以提醒对方</span>
      </div>
    </div>
    <p v-else class="mb-4 rounded-xl bg-[var(--pv-surface-2)] p-3 text-xs muted">UP 主已关闭该视频的评论。</p>

    <p v-if="loading" class="py-6 text-center text-sm muted">加载评论中…</p>
    <p v-else-if="!items.length" class="py-6 text-center text-sm muted">还没有评论，来抢沙发～</p>

    <ul v-else class="space-y-4">
      <li v-for="item in items" :key="item.id" class="flex gap-3">
        <RouterLink :to="`/space/${item.author?.username}`" class="shrink-0">
          <img v-if="item.author?.avatar" :src="item.author.avatar" class="h-9 w-9 rounded-full object-cover" alt="" />
          <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-[var(--pv-accent)]/15 text-sm font-semibold text-[var(--pv-accent)]">
            {{ initials(item.author?.displayName) }}
          </span>
        </RouterLink>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2 text-xs muted">
            <RouterLink :to="`/space/${item.author?.username}`" class="font-medium hover:text-[var(--pv-accent)]">
              {{ item.author?.displayName }}
            </RouterLink>
            <span v-if="item.isPinned" class="rounded bg-[var(--pv-accent)]/10 px-1 text-[var(--pv-accent)]">置顶</span>
            <span>{{ fromNow(item.createdAt) }}</span>
          </div>
          <p class="mt-1 whitespace-pre-wrap break-words text-sm" v-html="renderRich(item.content)" />
          <div class="mt-1 flex items-center gap-3 text-xs muted">
            <button class="inline-flex items-center gap-1" :class="item.liked ? 'text-rose-500' : 'hover:text-rose-500'" @click="like(item)">
              <Icon name="heart" :size="13" />{{ item.likeCount }}
            </button>
            <button v-if="allowComment" class="hover:text-[var(--pv-accent)]" @click="replyTo = item">回复</button>
            <button v-if="item.canDelete" class="hover:text-[var(--pv-accent)]" @click="pin(item)">{{ item.isPinned ? '取消置顶' : '置顶' }}</button>
            <button v-if="item.canDelete" class="hover:text-rose-500" @click="remove(item)">删除</button>
          </div>

          <ul v-if="item.replies?.length" class="mt-2 space-y-2 border-l-2 border-slate-100 pl-3">
            <li v-for="reply in item.replies" :key="reply.id" class="text-sm">
              <span class="text-xs text-[var(--pv-accent)]">{{ reply.author?.displayName }}</span>
              <span class="ml-2">{{ reply.content }}</span>
              <span class="ml-2 text-xs muted">{{ fromNow(reply.createdAt) }}</span>
            </li>
          </ul>
          <p v-if="item.replyCount > (item.replies?.length || 0)" class="mt-1 text-xs muted">
            共 {{ item.replyCount }} 条回复
          </p>
        </div>
      </li>
    </ul>

    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
  </section>
</template>
