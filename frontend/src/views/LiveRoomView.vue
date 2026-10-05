<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import Icon from '../components/Icon.vue';
import LivePlayer from '../components/LivePlayer.vue';
import LiveStudio from '../components/LiveStudio.vue';

const route = useRoute();
const store = useAppStore();
const room = ref<any>(null);
const playback = ref<any>({});
const studio = ref<any>(null);
const chat = ref<any[]>([]);
const draft = ref('');
const loading = ref(true);
const error = ref('');
const mine = ref<any>(null);
const chatBox = ref<HTMLElement | null>(null);
const view = ref<'studio' | 'watch'>('watch');
const studioTab = ref<'browser' | 'obs'>('browser');
const streamStatus = ref<{ status: string; source: string }>({ status: 'offline', source: '' });
const checking = ref(false);
let socket: WebSocket | null = null;
let pollTimer = 0;

const roomId = computed(() => Number(route.params.id || 0));
const ownerPath = computed(() => `/space/${room.value?.owner?.username || ''}`);
const isLive = computed(() => streamStatus.value.status === 'live' || room.value?.status === 'live');
const sourceLabel = computed(() =>
  streamStatus.value.source === 'rtmp' ? 'OBS 推流' : streamStatus.value.source === 'whip' ? '浏览器推流' : '',
);

function createRoom() {
  room.value = { title: '我的直播间', cover: '', description: '', playUrl: '' };
  void saveRoom();
}

async function load() {
  loading.value = true;
  try {
    if (!roomId.value) {
      mine.value = await api.get<any>('/api/live/mine');
      studio.value = mine.value.studio;
      room.value = mine.value.room;
      if (room.value) {
        const data = await api.get<any>(`/api/live/rooms/${room.value.id}`);
        chat.value = data.chat || [];
        playback.value = data.playback || {};
        room.value = data.room;
        streamStatus.value = { status: data.room.status, source: data.room.streamSource || '' };
      }
      view.value = 'studio';
      return;
    }
    const data = await api.get<any>(`/api/live/rooms/${roomId.value}`);
    room.value = data.room;
    playback.value = data.playback || {};
    chat.value = data.chat || [];
    streamStatus.value = { status: data.room.status, source: data.room.streamSource || '' };
    if (room.value.isMine) {
      const info = await api.get<any>(`/api/live/rooms/${roomId.value}/stream`);
      studio.value = info.studio;
      view.value = 'studio';
    }
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
        if (data.event === 'status') {
          streamStatus.value = { ...streamStatus.value, status: data.status };
          if (room.value) room.value.status = data.status;
        }
        if (data.event === 'error') toast.error(data.message);
      } catch {
        /* ignore */
      }
    };
  } catch {
    socket = null;
  }
}

/** 主播侧定期问一次「我现在到底在推流吗」，刷新页面也能立刻看到真实状态。 */
async function pollStream() {
  if (!room.value?.isMine) return;
  checking.value = true;
  try {
    const info = await api.get<any>(`/api/live/rooms/${room.value.id}/stream`);
    studio.value = info.studio;
    streamStatus.value = { status: info.status, source: info.streamSource || '' };
    if (room.value) room.value.status = info.status;
  } catch {
    /* 忽略，下次再试 */
  } finally {
    checking.value = false;
  }
}

function onStudioChanged(value: { status: string; source: string }) {
  streamStatus.value = value;
  if (room.value) room.value.status = value.status;
  window.setTimeout(() => void pollStream(), 1500);
}

async function copy(text: string, label: string) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label}已复制`);
  } catch {
    toast.error('复制失败，请手动选中复制');
  }
}

async function rotateKey() {
  if (!window.confirm('重新生成后旧密钥立刻失效，正在推流的软件需要重新填。确定继续吗？')) return;
  try {
    const data = await api.post<any>(`/api/live/rooms/${room.value.id}/stream-key/rotate`);
    studio.value = data.studio;
    toast.success('已重新生成串流密钥');
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '操作失败');
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

async function saveRoom() {
  try {
    const data = await api.post<any>('/api/live/rooms', {
      title: room.value.title,
      cover: room.value.cover,
      description: room.value.description,
      play_url: room.value.playUrl,
    });
    mine.value = data;
    studio.value = data.studio || studio.value;
    toast.success('直播间已保存');
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '保存失败');
  }
}

onMounted(async () => {
  await load();
  connect();
  if (room.value?.isMine) pollTimer = window.setInterval(pollStream, 8000);
});

onUnmounted(() => {
  socket?.close();
  window.clearInterval(pollTimer);
});
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <p v-else-if="error" class="surface p-16 text-center text-sm muted">{{ error }}</p>

  <div v-else-if="!room" class="surface space-y-3 p-8 text-center">
    <Icon name="radio" :size="28" class="mx-auto text-[var(--pv-accent)]" />
    <p class="text-sm">你还没有直播间</p>
    <p class="text-xs muted">{{ (mine && mine.notice) || '需要先由管理员开通直播权限。' }}</p>
    <button v-if="mine?.canLive" class="btn-primary" @click="createRoom">创建直播间</button>
  </div>

  <div v-else class="space-y-4">
    <!-- 主播：开播台 / 观众视角 切换 -->
    <div v-if="room.isMine" class="flex flex-wrap items-center gap-2">
      <div class="flex rounded-full bg-[var(--pv-surface-2)] p-0.5 text-xs">
        <button
          class="rounded-full px-3.5 py-1.5"
          :class="view === 'studio' ? 'bg-[var(--pv-surface)] font-medium' : 'muted'"
          @click="view = 'studio'"
        >
          开播台
        </button>
        <button
          class="rounded-full px-3.5 py-1.5"
          :class="view === 'watch' ? 'bg-[var(--pv-surface)] font-medium' : 'muted'"
          @click="view = 'watch'"
        >
          观众视角
        </button>
      </div>
      <span
        class="chip"
        :class="isLive ? '!border-rose-500/40 !text-rose-500' : ''"
      >
        <span class="h-1.5 w-1.5 rounded-full" :class="isLive ? 'animate-pulse bg-rose-500' : 'bg-slate-400'"></span>
        {{ isLive ? `直播中${sourceLabel ? ` · ${sourceLabel}` : ''}` : '未开播' }}
      </span>
      <button class="btn-ghost text-xs" :disabled="checking" @click="pollStream">
        <Icon name="refresh" :size="14" />{{ checking ? '刷新中…' : '刷新状态' }}
      </button>
    </div>

    <!-- 开播台 -->
    <div v-if="room.isMine && view === 'studio'" class="space-y-4">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-if="studio?.allowBrowser !== false"
          class="rounded-xl px-3.5 py-2 text-xs font-medium transition"
          :class="studioTab === 'browser' ? 'bg-[var(--pv-accent)] text-white' : 'bg-[var(--pv-surface-2)] muted'"
          @click="studioTab = 'browser'"
        >
          <Icon name="tv" :size="14" class="mr-1 inline" />网页开播
        </button>
        <button
          v-if="studio?.allowRtmp !== false"
          class="rounded-xl px-3.5 py-2 text-xs font-medium transition"
          :class="studioTab === 'obs' ? 'bg-[var(--pv-accent)] text-white' : 'bg-[var(--pv-surface-2)] muted'"
          @click="studioTab = 'obs'"
        >
          <Icon name="cpu" :size="14" class="mr-1 inline" />OBS 推流
        </button>
      </div>

      <LiveStudio
        v-if="studioTab === 'browser'"
        :studio="studio"
        :room-id="room.id"
        @changed="onStudioChanged"
      />

      <!-- OBS 面板 -->
      <div v-else-if="studio" class="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_320px]">
        <div class="surface space-y-3 p-4">
          <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="cpu" :size="16" />OBS / 推流软件设置</h2>
          <p class="text-xs muted">
            在 OBS 里打开「设置 → 直播」，服务选“自定义”，把下面两项分别填进去，然后点「开始推流」。
          </p>

          <div class="space-y-2">
            <div class="rounded-xl bg-[var(--pv-surface-2)] p-3">
              <div class="flex items-center gap-2">
                <span class="text-[11px] muted">服务器</span>
                <button class="ml-auto text-[11px] text-[var(--pv-accent)] hover:underline" @click="copy(studio?.rtmpServer, '服务器地址')">复制</button>
              </div>
              <p class="mt-1 break-all font-mono text-xs">{{ studio?.rtmpServer || '未配置' }}</p>
            </div>
            <div class="rounded-xl bg-[var(--pv-surface-2)] p-3">
              <div class="flex items-center gap-2">
                <span class="text-[11px] muted">串流密钥</span>
                <button class="ml-auto text-[11px] text-[var(--pv-accent)] hover:underline" @click="copy(studio?.streamKey, '串流密钥')">复制</button>
                <button class="text-[11px] text-rose-500 hover:underline" @click="rotateKey">重新生成</button>
              </div>
              <p class="mt-1 break-all font-mono text-xs">{{ studio?.streamKey || '—' }}</p>
            </div>
          </div>

          <div class="rounded-xl border border-[var(--pv-border)] p-3 text-xs muted">
            <p class="font-medium" style="color: var(--pv-text)">推荐推流参数</p>
            <ul class="mt-1.5 space-y-1">
              <li>· 输出：{{ studio?.defaultResolution || 720 }}p / {{ studio?.defaultFps || 30 }}fps</li>
              <li>· 码率：{{ studio?.maxBitrate || 6000 }} kbps 以内（本站上限）</li>
              <li>· 编码器：x264 或硬件编码，关键帧间隔 2 秒</li>
              <li>· 单场最长 {{ studio?.maxHours || 12 }} 小时，超时会自动断开</li>
            </ul>
          </div>
          <p class="text-[11px] muted">
            串流密钥等于开播密码，别发给别人。怀疑泄露就点「重新生成」。
          </p>
        </div>

        <div class="surface space-y-3 p-4">
          <h2 class="text-sm font-semibold">直播信息</h2>
          <div class="space-y-2">
            <div>
              <label class="label">标题</label>
              <input v-model="room.title" class="input" />
            </div>
            <div>
              <label class="label">简介</label>
              <textarea v-model="room.description" class="input min-h-[70px]"></textarea>
            </div>
            <div>
              <label class="label">播放地址（HLS）</label>
              <input :value="studio.hlsUrl" class="input" readonly />
              <p class="mt-1 text-[11px] muted">这个是自动生成的，不用自己填。</p>
            </div>
            <div>
              <label class="label">备用播放地址（可选）</label>
              <input v-model="room.playUrl" class="input" placeholder="没有内置接入时手填 HLS 地址" />
            </div>
          </div>
          <button class="btn-primary w-full text-xs" @click="saveRoom">保存设置</button>
        </div>
      </div>
    </div>

    <!-- 观众视角 -->
    <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_340px]">
      <div class="space-y-4">
        <LivePlayer
          :active="isLive"
          :whep-url="playback.whepUrl"
          :hls-url="playback.hlsUrl || room.playUrl"
          :prefer-webrtc="playback.preferWebrtc !== false"
          :poster="room.cover"
          :title="room.description"
        />

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
                <span v-if="isLive && room.startedAt"> · {{ fromNow(room.startedAt) }}开播</span>
              </p>
            </div>
            <button v-if="room.isMine" class="btn-ghost text-xs" @click="view = 'studio'">
              <Icon name="settings" :size="15" />开播设置
            </button>
          </div>
          <p v-if="room.description" class="mt-3 border-t border-[var(--pv-border)] pt-3 text-sm muted">{{ room.description }}</p>
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
  </div>
</template>
