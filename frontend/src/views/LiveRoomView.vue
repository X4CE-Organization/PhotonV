<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import Icon from '../components/Icon.vue';

const route = useRoute();
const store = useAppStore();
const room = ref<any>(null);
const chat = ref<any[]>([]);
const draft = ref('');
const loading = ref(true);
const error = ref('');
const mine = ref<any>(null);
const chatBox = ref<HTMLElement | null>(null);
let socket: WebSocket | null = null;

const roomId = computed(() => Number(route.params.id || 0));
const ownerPath = computed(() => `/space/${room.value?.owner?.username || ''}`);

function createRoom() {
  room.value = { title: '我的直播间', cover: '', description: '', playUrl: '' };
  void saveRoom();
}

async function load() {
  loading.value = true;
  try {
    if (!roomId.value) {
      mine.value = await api.get<any>('/api/live/mine');
      room.value = mine.value.room;
      if (room.value) {
        const data = await api.get<any>(`/api/live/rooms/${room.value.id}`);
        chat.value = data.chat || [];
        room.value = data.room;
      }
      return;
    }
    const data = await api.get<any>(`/api/live/rooms/${roomId.value}`);
    room.value = data.room;
    chat.value = data.chat || [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : '直播间不存在';
  } finally {
    loading.value = false;
  }
}

function connect() {
  if (!room.value?.id || !store.isLogin) return;
  const token = localStorage.getItem('photonv-token') || '';
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  socket?.close();
  try {
    socket = new WebSocket(`${protocol}://${location.host}/ws/live/${room.value.id}?token=${encodeURIComponent(token)}`);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'chat') {
          chat.value.push(data);
          if (chat.value.length > 200) chat.value.shift();
          requestAnimationFrame(() => {
            if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight;
          });
        }
        if (data.event === 'status') room.value.status = data.status;
        if (data.event === 'error') toast.error(data.message);
      } catch {
        /* ignore */
      }
    };
  } catch {
    socket = null;
  }
}

function send() {
  const content = draft.value.trim();
  if (!content) return;
  if (!store.isLogin) return toast.info('登录后才能发言');
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ content }));
    draft.value = '';
    return;
  }
  void api.post(`/api/live/rooms/${room.value.id}/chat`, { content }).catch((err) => {
    toast.error(err instanceof Error ? err.message : '发送失败');
  });
  draft.value = '';
}

async function toggleLive() {
  try {
    const next = room.value.status === 'live' ? 'offline' : 'live';
    const data = await api.post<any>(`/api/live/rooms/${room.value.id}/status`, { status: next });
    room.value.status = data.status;
    toast.success(next === 'live' ? '已开播' : '已下播');
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '操作失败');
  }
}

async function saveRoom() {
  try {
    const data = await api.post<any>('/api/live/rooms', {
      title: room.value.title,
      cover: room.value.cover,
      description: room.value.description,
      play_url: room.value.playUrl,
    });
    mine.value = data;
    toast.success('直播间已保存');
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '保存失败');
  }
}

onMounted(async () => {
  await load();
  connect();
});

onUnmounted(() => socket?.close());
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <p v-else-if="error" class="surface p-16 text-center text-sm muted">{{ error }}</p>

  <div v-else-if="!room" class="surface space-y-3 p-8 text-center">
    <Icon name="radio" :size="28" class="mx-auto text-[var(--pv-accent)]" />
    <p class="text-sm">你还没有直播间</p>
    <p class="text-xs muted">{{ (mine && mine.notice) || '需要先由管理员开通直播权限。' }}</p>
    <button v-if="mine?.canLive" class="btn-primary" @click="createRoom">
      创建直播间
    </button>
  </div>

  <div v-else class="grid gap-4 lg:grid-cols-[1fr_340px]">
    <div class="space-y-4">
      <div class="player-shell aspect-video">
        <video v-if="room.playUrl" :src="room.playUrl" class="h-full w-full" controls autoplay playsinline :poster="room.cover"></video>
        <div v-else class="grid h-full w-full place-items-center bg-gradient-to-br from-[#12121c] to-[#1b1430] text-center text-white">
          <div class="space-y-3">
            <Icon name="radio" :size="34" class="mx-auto opacity-80" />
            <p class="text-sm font-medium">{{ room.status === 'live' ? '主播正在直播' : '主播还没开播' }}</p>
            <p class="mx-auto max-w-sm text-xs opacity-70">
              配置好推流地址后，把播放地址（HLS / http-flv）填进直播间设置即可在这里播放。
            </p>
          </div>
        </div>
        <span
          v-if="room.status === 'live'"
          class="absolute left-3 top-3 rounded-md bg-rose-500 px-2 py-0.5 text-[11px] font-semibold text-white"
        >LIVE</span>
      </div>

      <div class="surface p-4">
        <div class="flex flex-wrap items-center gap-3">
          <RouterLink :to="ownerPath" class="shrink-0">
            <img v-if="room.owner?.avatar" :src="room.owner.avatar" class="h-12 w-12 rounded-full object-cover" alt="" />
            <span v-else class="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] font-bold text-white">
              {{ initials(room.owner?.displayName) }}
            </span>
          </RouterLink>
          <div class="min-w-0 flex-1">
            <h1 class="text-base font-semibold">{{ room.title }}</h1>
            <p class="mt-0.5 text-xs muted">
              {{ room.owner?.displayName }} · {{ formatNumber(room.viewers) }} 人气 · {{ formatNumber(room.chatCount) }} 条聊天
              <span v-if="room.startedAt"> · {{ fromNow(room.startedAt) }}开播</span>
            </p>
          </div>
          <button
            v-if="room.canManage"
            class="btn-primary text-xs"
            @click="toggleLive"
          >
            {{ room.status === 'live' ? '下播' : '开播' }}
          </button>
        </div>
        <p v-if="room.description" class="mt-3 border-t border-[var(--pv-border)] pt-3 text-sm muted">{{ room.description }}</p>
      </div>

      <div v-if="room.isMine" class="surface space-y-3 p-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="settings" :size="16" />直播间设置</h2>
        <div class="grid gap-3 sm:grid-cols-2">
          <div><label class="label">标题</label><input v-model="room.title" class="input" /></div>
          <div><label class="label">播放地址（HLS）</label><input v-model="room.playUrl" class="input" placeholder="https://.../index.m3u8" /></div>
        </div>
        <div><label class="label">简介</label><textarea v-model="room.description" class="input min-h-[70px]"></textarea></div>
        <div class="rounded-xl bg-[var(--pv-surface-2)] p-3 text-xs">
          <div class="muted">推流地址（OBS → 服务器）</div>
          <div class="mt-1 break-all font-mono">{{ mine?.pushUrl }}</div>
          <div class="mt-2 muted">流密钥</div>
          <div class="mt-1 break-all font-mono">{{ mine?.room?.streamKey }}</div>
        </div>
        <div class="flex justify-end"><button class="btn-primary text-xs" @click="saveRoom">保存设置</button></div>
      </div>
    </div>

    <aside class="surface flex h-[560px] flex-col overflow-hidden">
      <div class="flex items-center gap-2 border-b border-[var(--pv-border)] px-3 py-2.5 text-sm">
        <Icon name="message" :size="16" />直播聊天
        <span class="ml-auto text-xs muted">{{ chat.length }} 条</span>
      </div>
      <div ref="chatBox" class="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
        <div v-for="item in chat" :key="item.id" class="flex gap-2">
          <img v-if="item.user?.avatar" :src="item.user.avatar" class="h-6 w-6 rounded-full object-cover" alt="" />
          <span v-else class="grid h-6 w-6 place-items-center rounded-full bg-[var(--pv-surface-2)] text-[10px] font-bold">
            {{ initials(item.user?.displayName) }}
          </span>
          <div class="min-w-0">
            <span class="text-xs text-[var(--pv-accent)]">{{ item.user?.displayName }}</span>
            <p class="break-words text-[13px]">{{ item.content }}</p>
          </div>
        </div>
        <p v-if="!chat.length" class="py-8 text-center text-xs muted">还没有人说话</p>
      </div>
      <div class="flex items-center gap-2 border-t border-[var(--pv-border)] p-2.5">
        <input
          v-model="draft"
          class="input flex-1"
          :maxlength="Number(store.settings.live_chat_max_length || 100)"
          :placeholder="store.isLogin ? '说点什么…' : '登录后参与聊天'"
          :disabled="!store.isLogin"
          @keyup.enter="send"
        />
        <button class="btn-primary !px-3" :disabled="!store.isLogin || !draft.trim()" @click="send">
          <Icon name="send" :size="16" />
        </button>
      </div>
    </aside>
  </div>
</template>
