<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import { startWhep, type WhepHandle } from '../composables/webrtc';
import Icon from './Icon.vue';

const props = defineProps<{
  active: boolean;
  whepUrl?: string;
  hlsUrl?: string;
  preferWebrtc?: boolean;
  poster?: string;
  title?: string;
}>();

const video = ref<HTMLVideoElement | null>(null);
const mode = ref<'idle' | 'webrtc' | 'hls' | 'error'>('idle');
const detail = ref('');
let handle: WhepHandle | null = null;

function teardown() {
  handle?.stop();
  handle = null;
}

async function play() {
  teardown();
  mode.value = 'idle';
  detail.value = '';
  if (!props.active || !video.value) return;

  const element = video.value;
  const wantWebrtc = props.preferWebrtc !== false && Boolean(props.whepUrl);
  if (wantWebrtc) {
    try {
      handle = await startWhep(props.whepUrl as string, element);
      mode.value = 'webrtc';
      return;
    } catch (error) {
      teardown();
      detail.value = error instanceof Error ? error.message : '';
      // WebRTC 不通就退回 HLS，兼容性优先
    }
  }

  if (props.hlsUrl) {
    element.srcObject = null;
    element.src = props.hlsUrl;
    mode.value = 'hls';
    void element.play().catch(() => undefined);
    return;
  }
  mode.value = wantWebrtc ? 'error' : 'idle';
}

watch(() => [props.active, props.whepUrl, props.hlsUrl], () => void play());
onBeforeUnmount(teardown);
</script>

<template>
  <div class="player-shell aspect-video">
    <video ref="video" class="h-full w-full bg-black" controls autoplay playsinline :poster="poster"></video>

    <div v-if="!active" class="absolute inset-0 grid place-items-center bg-gradient-to-br from-[#12121c] to-[#1b1430] text-center text-white">
      <div class="space-y-3">
        <Icon name="radio" :size="34" class="mx-auto opacity-80" />
        <p class="text-sm font-medium">主播还没开播</p>
        <p class="mx-auto max-w-sm text-xs opacity-70">{{ title || '开播后这里会自动出现画面' }}</p>
      </div>
    </div>

    <span v-if="active" class="absolute left-3 top-3 flex items-center gap-1.5 rounded-md bg-rose-500 px-2 py-0.5 text-[11px] font-semibold text-white">
      <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-white"></span>LIVE
    </span>
    <span v-if="active && mode === 'webrtc'" class="absolute right-3 top-3 rounded-md bg-black/60 px-2 py-0.5 text-[11px] text-white">
      超低延迟
    </span>
    <span v-else-if="active && mode === 'hls'" class="absolute right-3 top-3 rounded-md bg-black/60 px-2 py-0.5 text-[11px] text-white">
      HLS
    </span>
  </div>
</template>
