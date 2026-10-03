<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { fromNow, initials, renderRich } from '../utils';
import Icon from '../components/Icon.vue';
import EmojiPicker from '../components/EmojiPicker.vue';

const store = useAppStore();
const route = useRoute();
const conversations = ref<any[]>([]);
const active = ref<any>(null);
const messages = ref<any[]>([]);
const draft = ref('');
const showEmoji = ref(false);

function insertEmoji(token: string) {
  draft.value = `${draft.value}${draft.value && !draft.value.endsWith(' ') ? ' ' : ''}${token} `;
  showEmoji.value = false;
}
const loading = ref(true);
const box = ref<HTMLElement | null>(null);
let socket: WebSocket | null = null;

async function loadConversations() {
  const data = await api.get<any>('/api/messages/conversations');
  conversations.value = data.items || [];
  if (!active.value && conversations.value.length) await open(conversations.value[0]);
}

async function open(item: any) {
  active.value = item;
  const data = await api.get<any>(`/api/messages/${item.id}?size=60`);
  messages.value = data.items || [];
  item.unread = 0;
  requestAnimationFrame(scrollBottom);
}

function scrollBottom() {
  if (box.value) box.value.scrollTop = box.value.scrollHeight;
}

async function send() {
  const content = draft.value.trim();
  if (!content || !active.value) return;
  try {
    await api.post('/api/messages', { to_user_id: active.value.user.id, content });
    messages.value.push({
      id: Date.now(),
      content,
      createdAt: new Date().toISOString().slice(0, 19).replace('T', ' '),
      mine: true,
    });
    draft.value = '';
    active.value.lastMessage = content;
    requestAnimationFrame(scrollBottom);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '发送失败');
  }
}

async function removeConversation(item: any, event: Event) {
  event.stopPropagation();
  if (!window.confirm(`确定删除与 ${item.user.displayName} 的会话吗？`)) return;
  await api.del(`/api/messages/${item.id}`);
  conversations.value = conversations.value.filter((row) => row.id !== item.id);
  if (active.value?.id === item.id) {
    active.value = null;
    messages.value = [];
  }
  toast.success('已删除');
}

function connect() {
  const token = localStorage.getItem('photonv-token') || '';
  if (!token) return;
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  try {
    socket = new WebSocket(`${protocol}://${location.host}/ws/messages?token=${encodeURIComponent(token)}`);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event !== 'message') return;
        const existing = conversations.value.find((row) => row.id === data.conversationId);
        if (existing) {
          existing.lastMessage = data.message.content;
          existing.lastAt = data.message.createdAt;
          if (active.value?.id !== existing.id) existing.unread = (existing.unread || 0) + 1;
        } else {
          void loadConversations();
        }
        if (active.value?.id === data.conversationId) {
          messages.value.push(data.message);
          requestAnimationFrame(scrollBottom);
        }
      } catch {
        /* ignore */
      }
    };
  } catch {
    socket = null;
  }
}

onMounted(async () => {
  try {
    await loadConversations();
    const target = String(route.query.to || '');
    if (target) {
      const existing = conversations.value.find((item) => item.user?.username === target);
      if (existing) {
        await open(existing);
      } else {
        const profile = await api.get<any>(`/api/users/${encodeURIComponent(target)}`);
        active.value = {
          id: 0,
          pending: true,
          user: {
            id: profile.profile.id,
            username: target,
            displayName: profile.profile.displayName,
          },
          lastMessage: '',
          unread: 0,
        };
        messages.value = [];
      }
    }
  } finally {
    loading.value = false;
  }
  connect();
});

onUnmounted(() => socket?.close());
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-[300px_1fr]">
    <aside class="surface overflow-hidden">
      <div class="flex items-center gap-2 border-b border-[var(--pv-border)] px-4 py-3 text-sm font-semibold">
        <Icon name="message" :size="17" />私信
        <span class="ml-auto text-xs muted">{{ conversations.length }} 个会话</span>
      </div>
      <p v-if="loading" class="py-10 text-center text-xs muted">加载中…</p>
      <ul v-else-if="!conversations.length" class="p-8 text-center text-xs muted">
        还没有私信，去别人的个人空间点「发私信」试试
      </ul>
      <ul v-else class="max-h-[560px] overflow-y-auto">
        <li v-for="item in conversations" :key="item.id">
          <button
            class="flex w-full items-center gap-3 px-3 py-2.5 text-left transition"
            :class="active?.id === item.id ? 'bg-[var(--pv-accent)]/10' : 'hover:bg-[var(--pv-surface-2)]'"
            @click="open(item)"
          >
            <img v-if="item.user?.avatar" :src="item.user.avatar" class="h-9 w-9 rounded-full object-cover" alt="" />
            <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-xs font-bold text-white">
              {{ initials(item.user?.displayName) }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-2">
                <span class="truncate text-sm">{{ item.user?.displayName }}</span>
                <span v-if="item.unread" class="rounded-full bg-rose-500 px-1.5 text-[10px] text-white">{{ item.unread }}</span>
                <span class="ml-auto shrink-0 text-[11px] muted">{{ fromNow(item.lastAt) }}</span>
              </span>
              <span class="mt-0.5 block truncate text-xs muted">{{ item.lastMessage }}</span>
            </span>
            <span class="shrink-0 text-xs muted hover:text-rose-500" @click="removeConversation(item, $event)">
              <Icon name="trash" :size="14" />
            </span>
          </button>
        </li>
      </ul>
    </aside>

    <section class="surface flex h-[620px] flex-col overflow-hidden">
      <template v-if="active">
        <div class="flex items-center gap-3 border-b border-[var(--pv-border)] px-4 py-3">
          <RouterLink :to="`/space/${active.user.username}`" class="text-sm font-semibold hover:text-[var(--pv-accent)]">
            {{ active.user.displayName }}
          </RouterLink>
          <span class="text-xs muted">@{{ active.user.username }}</span>
        </div>
        <div ref="box" class="flex-1 space-y-3 overflow-y-auto p-4">
          <div v-for="item in messages" :key="item.id" class="flex" :class="item.mine ? 'justify-end' : 'justify-start'">
            <div
              class="max-w-[70%] rounded-2xl px-3.5 py-2 text-sm"
              :class="item.mine ? 'bg-gradient-to-br from-[#6d4aff] to-[#8b5cf6] text-white' : 'bg-[var(--pv-surface-2)]'"
            >
              <p class="whitespace-pre-wrap break-words" v-html="renderRich(item.content)" />
              <div class="mt-1 text-[10px] opacity-70">{{ fromNow(item.createdAt) }}</div>
            </div>
          </div>
        </div>
        <div class="relative flex items-center gap-2 border-t border-[var(--pv-border)] p-3">
          <button class="btn-ghost !px-2" title="表情" @click="showEmoji = !showEmoji"><Icon name="sparkles" :size="16" /></button>
          <div v-if="showEmoji" class="absolute bottom-full left-3 z-30 mb-2">
            <EmojiPicker @pick="insertEmoji" />
          </div>
          <input v-model="draft" class="input flex-1" placeholder="输入消息，回车发送" @keyup.enter="send" />
          <button class="btn-primary !px-3" :disabled="!draft.trim()" @click="send"><Icon name="send" :size="16" /></button>
        </div>
      </template>
      <div v-else class="grid flex-1 place-items-center text-sm muted">
        <div class="text-center">
          <Icon name="message" :size="30" class="mx-auto mb-2 opacity-60" />
          选择左侧会话开始聊天
        </div>
      </div>
    </section>
  </div>
</template>
