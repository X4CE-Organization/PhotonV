<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatDuration } from '../utils';

const props = defineProps<{
  video: any;
  danmaku: any[];
  allowDanmaku: boolean;
  quality?: string;
  variants?: any[];
}>();
const emit = defineEmits<{ (event: 'sent', item: any): void; (event: 'quality', value: string): void }>();

const store = useAppStore();
const videoEl = ref<HTMLVideoElement | null>(null);
const shell = ref<HTMLElement | null>(null);
const playing = ref(false);
const current = ref(0);
const duration = ref(0);
const volume = ref(0.8);
const rate = ref(1);
const showDanmaku = ref(true);
const opacity = ref(Number(store.settings.danmaku_opacity || 90) / 100);
const input = ref('');
const color = ref('#ffffff');
const mode = ref<'scroll' | 'top' | 'bottom'>('scroll');
const sending = ref(false);
const showSettings = ref(false);
const fontSize = ref(Math.max(12, Math.min(32, Number(store.settings.danmaku_font_size || 18))));
const active = ref<any[]>([]);
const busy = ref<number[]>([]);
const shown = new Set<number>();
let frame = 0;
let lastProgressSent = 0;

const scrollSeconds = computed(() => Math.max(4, Number(store.settings.danmaku_speed || 8)));
const progressPercent = computed(() => (duration.value ? (current.value / duration.value) * 100 : 0));
const currentSrc = computed(() => {
  const list = props.variants || [];
  if (props.quality && props.quality !== 'auto') {
    const matched = list.find((item: any) => item.quality === props.quality);
    if (matched) return matched.url;
  }
  return props.video.source || props.video.sourceUrl;
});

function trackCount() {
  const height = shell.value?.clientHeight || 400;
  const line = fontSize.value + 8;
  return Math.max(3, Math.floor((height * 0.78) / line));
}

function pickTrack(): number {
  const now = performance.now();
  const total = trackCount();
  if (busy.value.length !== total) busy.value = new Array(total).fill(0);
  for (let index = 0; index < total; index += 1) {
    if (busy.value[index] <= now) return index;
  }
  let best = 0;
  for (let index = 1; index < total; index += 1) {
    if (busy.value[index] < busy.value[best]) best = index;
  }
  return best;
}

function spawn(item: any, atTime: number) {
  const track = pickTrack();
  const durationMs = item.mode === 'scroll' ? scrollSeconds.value * 1000 : 4000;
  busy.value[track] = performance.now() + (item.mode === 'scroll' ? durationMs * 0.75 : 2200);
  const entry = {
    key: `${item.id}-${Math.random().toString(36).slice(2, 7)}`,
    content: item.content,
    color: item.color || '#ffffff',
    fontSize: item.fontSize || fontSize.value,
    mode: item.mode || 'scroll',
    top: item.mode === 'scroll' ? 10 + track * (fontSize.value + 8) : item.mode === 'top' ? 14 + track * 4 : undefined,
    bottom: item.mode === 'bottom' ? 60 + track * 4 : undefined,
    duration: durationMs,
  };
  active.value.push(entry);
  window.setTimeout(() => {
    active.value = active.value.filter((row) => row.key !== entry.key);
  }, durationMs + 60);
  void atTime;
}

function tick() {
  const element = videoEl.value;
  if (element && showDanmaku.value) {
    const time = element.currentTime;
    for (const item of props.danmaku) {
      if (shown.has(item.id)) continue;
      if (item.time <= time && time - item.time < 0.6) {
        shown.add(item.id);
        spawn(item, item.time);
      }
    }
  }
  frame = requestAnimationFrame(tick);
}

function togglePlay() {
  const element = videoEl.value;
  if (!element) return;
  if (element.paused) void element.play();
  else element.pause();
}

function onTimeUpdate() {
  const element = videoEl.value;
  if (!element) return;
  current.value = element.currentTime;
  if (current.value - lastProgressSent > 10 && store.isLogin) {
    lastProgressSent = current.value;
    void api
      .post(`/api/videos/${props.video.id}/progress`, {
        progress: Math.floor(current.value),
        duration: Math.floor(element.duration || 0),
      })
      .catch(() => undefined);
  }
}

function seek(event: MouseEvent) {
  const element = videoEl.value;
  if (!element || !duration.value) return;
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  element.currentTime = ratio * duration.value;
  shown.clear();
  active.value = [];
  busy.value = [];
}

async function send() {
  const content = input.value.trim();
  if (!content) return;
  if (!store.isLogin) {
    toast.info('登录后才能发送弹幕');
    return;
  }
  sending.value = true;
  try {
    const item = await api.post<any>(`/api/videos/${props.video.id}/danmaku`, {
      content,
      time: current.value,
      color: color.value,
      mode: mode.value,
      font_size: fontSize.value,
    });
    input.value = '';
    emit('sent', item);
    spawn({ ...item, time: current.value }, current.value);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '发送失败');
  } finally {
    sending.value = false;
  }
}

function toggleFullscreen() {
  const element = shell.value;
  if (!element) return;
  if (document.fullscreenElement) void document.exitFullscreen();
  else void element.requestFullscreen();
}

/** 供父组件使用的播放控制：读当前进度、跳到指定秒数。 */
defineExpose({
  position: () => current.value,
  seekTo: (seconds: number) => {
    const element = videoEl.value;
    if (!element) return;
    element.currentTime = Math.max(0, seconds);
    shown.clear();
    active.value = [];
    busy.value = [];
    void element.play().catch(() => undefined);
  },
});

watch(
  () => props.video?.id,
  () => {
    shown.clear();
    active.value = [];
    busy.value = [];
    current.value = 0;
  },
);

onMounted(() => {
  frame = requestAnimationFrame(tick);
});

onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
});
</script>

<template>
  <div ref="shell" class="player-shell group">
    <video
      ref="videoEl"
      class="aspect-video w-full bg-black"
      :src="currentSrc"
      :poster="video.cover"
      :autoplay="store.settings.player_autoplay !== false"
      controls
      playsinline
      @play="playing = true"
      @pause="playing = false"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="duration = (videoEl?.duration || video.duration || 0)"
    ></video>

    <div v-show="showDanmaku" class="danmaku-layer" :style="{ opacity }">
      <div
        v-for="item in active"
        :key="item.key"
        class="danmaku-item"
        :class="item.mode === 'scroll' ? 'danmaku-scroll' : ''"
        :style="{
          color: item.color,
          fontSize: item.fontSize + 'px',
          top: item.mode !== 'bottom' ? (item.top || 16) + 'px' : undefined,
          bottom: item.mode === 'bottom' ? (item.bottom || 60) + 'px' : undefined,
          left: item.mode === 'scroll' ? undefined : '50%',
          transform: item.mode === 'scroll' ? undefined : 'translateX(-50%)',
          animationDuration: item.duration + 'ms',
        }"
      >
        {{ item.content }}
      </div>
    </div>
  </div>

  <div class="mt-3 flex flex-wrap items-center gap-2">
    <div class="flex min-w-[220px] flex-1 items-center gap-2">
      <span class="text-xs text-slate-400">{{ formatDuration(current) }} / {{ formatDuration(duration || video.duration) }}</span>
      <div class="h-1.5 flex-1 cursor-pointer rounded-full bg-slate-200 dark:bg-slate-700" @click="seek">
        <div class="h-full rounded-full bg-primary" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>
    <label class="flex items-center gap-1 text-xs text-slate-500">
      <input v-model="showDanmaku" type="checkbox" :disabled="!allowDanmaku" />
      弹幕
    </label>
    <select v-model.number="rate" class="input !w-20 !py-1 text-xs" @change="videoEl && (videoEl.playbackRate = rate)">
      <option :value="0.5">0.5x</option>
      <option :value="1">1.0x</option>
      <option :value="1.25">1.25x</option>
      <option :value="1.5">1.5x</option>
      <option :value="2">2.0x</option>
    </select>
    <select
      v-if="variants && variants.length > 1"
      class="input !w-24 !py-1 text-xs"
      :value="quality || 'auto'"
      @change="emit('quality', (($event.target as HTMLSelectElement).value))"
    >
      <option value="auto">自动</option>
      <option v-for="item in variants" :key="item.quality" :value="item.quality">{{ item.label }}</option>
    </select>
    <button class="btn-ghost !px-2 !py-1 text-xs" @click="showSettings = !showSettings">弹幕设置</button>
    <button class="btn-ghost !px-2 !py-1 text-xs" @click="toggleFullscreen">全屏</button>
    <a v-if="video.allowDownload && video.source" :href="video.source" download class="btn-ghost !px-2 !py-1 text-xs">下载</a>
  </div>

  <div v-if="showSettings" class="mt-2 flex flex-wrap items-center gap-3 rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
    <label class="flex items-center gap-1">不透明度
      <input v-model.number="opacity" type="range" min="0.1" max="1" step="0.05" />
    </label>
    <label class="flex items-center gap-1">字号
      <input v-model.number="fontSize" type="range" min="12" max="30" step="1" />
      <span class="muted">{{ fontSize }}px</span>
    </label>
    <span>显示模式：</span>
    <select v-model="mode" class="input !w-24 !py-1 text-xs">
      <option value="scroll">滚动</option>
      <option value="top">顶部</option>
      <option value="bottom">底部</option>
    </select>
    <span>颜色：</span>
    <input v-model="color" type="color" class="h-7 w-10 rounded border border-slate-200 bg-white" />
  </div>

  <div class="mt-2 flex items-center gap-2">
    <input
      v-model="input"
      class="input flex-1"
      maxlength="60"
      :disabled="!allowDanmaku"
      :placeholder="allowDanmaku ? '发一条弹幕吧，回车发送' : '该视频已关闭弹幕'"
      @keyup.enter="send"
    />
    <button class="btn-primary !px-3" :disabled="sending || !allowDanmaku" @click="send">发送</button>
  </div>
</template>
