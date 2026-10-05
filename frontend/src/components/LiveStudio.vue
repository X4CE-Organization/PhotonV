<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { captureSupported, sampleStats, screenShareSupported, startWhip, stopWhip, type WhipHandle } from '../composables/webrtc';
import { toast } from '../composables/toast';
import Icon from './Icon.vue';

const props = defineProps<{ studio: any; roomId: number | null }>();
const emit = defineEmits<{ (event: 'changed', value: { status: string; source: string }): void }>();

type SourceKind = 'screen' | 'camera' | 'pip';

const sourceKind = ref<SourceKind>('screen');
const resolution = ref<number>(Number(props.studio?.defaultResolution) || 720);
const fps = ref<number>(Number(props.studio?.defaultFps) || 30);
const bitrate = ref<number>(Number(props.studio?.maxBitrate) || 6000);
const audioEnabled = ref(true);

const cameras = ref<MediaDeviceInfo[]>([]);
const microphones = ref<MediaDeviceInfo[]>([]);
const cameraId = ref('');
const micId = ref('');

const preview = ref<HTMLVideoElement | null>(null);
const cameraPreview = ref<HTMLVideoElement | null>(null);
const publishing = ref(false);
const connecting = ref(false);
const connectionState = ref('');
const elapsed = ref(0);
const stats = ref({ bitrate: 0, fps: 0, width: 0, height: 0, packetsLost: 0 });
const errorText = ref('');

let stream: MediaStream | null = null;
let screenStream: MediaStream | null = null;
let cameraStream: MediaStream | null = null;
let handle: WhipHandle | null = null;
let compositeTimer = 0;
let statsTimer = 0;
let clockTimer = 0;
let lastBytes = 0;
let lastStamp = 0;

const supported = computed(() => captureSupported());
const canScreen = computed(() => screenShareSupported());
const whipUrl = computed(() => String(props.studio?.whipUrl || ''));
const allowBrowser = computed(() => props.studio?.allowBrowser !== false && props.studio?.ingestEnabled !== false);
const ready = computed(() => Boolean(whipUrl.value) && allowBrowser.value);

const height = computed(() => ({ 480: 480, 720: 720, 1080: 1080 }[resolution.value] || 720));

function clock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':');
}

function mbit(value: number): string {
  return `${(value / 1000).toFixed(2)} Mbps`;
}

async function loadDevices() {
  try {
    const list = await navigator.mediaDevices.enumerateDevices();
    cameras.value = list.filter((item) => item.kind === 'videoinput');
    microphones.value = list.filter((item) => item.kind === 'audioinput');
    if (!cameraId.value && cameras.value[0]) cameraId.value = cameras.value[0].deviceId;
    if (!micId.value && microphones.value[0]) micId.value = microphones.value[0].deviceId;
  } catch {
    /* 没有权限时拿不到设备名，等开始推流后再刷新 */
  }
}

function stopStream(target: MediaStream | null) {
  target?.getTracks().forEach((track) => track.stop());
}

/** 把屏幕和摄像头合成画中画：摄像头放在右下角。 */
function composePip(screen: MediaStream, camera: MediaStream): MediaStream {
  const canvas = document.createElement('canvas');
  const video = document.createElement('video');
  const cam = document.createElement('video');
  video.srcObject = screen;
  cam.srcObject = camera;
  video.muted = true;
  cam.muted = true;
  void video.play();
  void cam.play();

  const ctx = canvas.getContext('2d');
  compositeTimer = window.setInterval(() => {
    const width = video.videoWidth || 1280;
    const h = video.videoHeight || 720;
    if (canvas.width !== width || canvas.height !== h) {
      canvas.width = width;
      canvas.height = h;
    }
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, width, h);
    const boxW = Math.round(width * 0.24);
    const boxH = Math.round(boxW * 0.5625);
    const pad = Math.round(width * 0.02);
    const x = width - boxW - pad;
    const y = h - boxH - pad;
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(x, y, boxW, boxH, 12);
    ctx.clip();
    ctx.drawImage(cam, x, y, boxW, boxH);
    ctx.restore();
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, boxW, boxH);
  }, 1000 / Math.max(15, fps.value));

  const composed = canvas.captureStream(fps.value);
  camera.getAudioTracks().forEach((track) => composed.addTrack(track));
  return composed;
}

async function buildStream(): Promise<MediaStream> {
  const videoConstraints = {
    width: { ideal: Math.round((height.value * 16) / 9) },
    height: { ideal: height.value },
    frameRate: { ideal: fps.value, max: fps.value },
    ...(cameraId.value ? { deviceId: { exact: cameraId.value } } : {}),
  };
  const audioConstraints = audioEnabled.value
    ? { ...(micId.value ? { deviceId: { exact: micId.value } } : {}) }
    : false;

  if (sourceKind.value === 'camera') {
    stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: audioConstraints });
    return stream;
  }

  if (!canScreen.value) throw new Error('当前环境不支持屏幕共享（需要 https 或 localhost）');
  screenStream = await navigator.mediaDevices.getDisplayMedia({
    video: { frameRate: { ideal: fps.value, max: fps.value } },
    audio: false,
  });
  if (preview.value) preview.value.srcObject = screenStream;

  if (sourceKind.value === 'screen') {
    stream = screenStream;
    if (!audioEnabled.value) return screenStream;
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: audioConstraints });
    cameraStream.getAudioTracks().forEach((track) => screenStream!.addTrack(track));
    return screenStream;
  }

  cameraStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: audioConstraints });
  if (cameraPreview.value) cameraPreview.value.srcObject = cameraStream;
  stream = composePip(screenStream, cameraStream);
  return stream;
}

async function start() {
  if (!ready.value) {
    toast.error('还没有配置好推流地址，请检查后台「直播」设置');
    return;
  }
  if (!props.roomId) {
    toast.error('请先创建直播间');
    return;
  }
  errorText.value = '';
  connecting.value = true;
  try {
    // 只有已经拿到授权后，设备列表里才会有名字
    await loadDevices();
    const media = await buildStream();
    if (sourceKind.value !== 'pip' && preview.value) preview.value.srcObject = media;

    handle = await startWhip(whipUrl.value, media, (state) => {
      connectionState.value = state;
      if (state === 'failed') {
        errorText.value = '推流连接断开，请检查网络或服务器时间是否准确';
      }
    });

    // 码率上限
    const sender = handle.pc.getSenders().find((item) => item.track?.kind === 'video');
    if (sender) {
      const params = sender.getParameters();
      params.encodings = params.encodings?.length ? params.encodings : [{}];
      params.encodings[0].maxBitrate = Math.max(200, bitrate.value) * 1000;
      await sender.setParameters(params).catch(() => undefined);
    }

    publishing.value = true;
    connectionState.value = handle.pc.connectionState;
    elapsed.value = 0;
    lastBytes = 0;
    lastStamp = 0;
    clockTimer = window.setInterval(() => (elapsed.value += 1), 1000);
    statsTimer = window.setInterval(async () => {
      if (!handle) return;
      const sample = await sampleStats(handle.pc);
      if (!sample) return;
      const stamp = performance.now();
      if (lastStamp && sample.bitrate >= lastBytes) {
        const kbps = ((sample.bitrate - lastBytes) * 8) / (stamp - lastStamp);
        stats.value = { ...sample, bitrate: kbps };
      } else {
        stats.value = { ...sample, bitrate: 0 };
      }
      lastBytes = sample.bitrate;
      lastStamp = stamp;
    }, 2000);

    // 用户点了浏览器自带的「停止共享」
    media.getVideoTracks().forEach((track) => {
      track.addEventListener('ended', () => {
        if (publishing.value) void stop();
      });
    });

    emit('changed', { status: 'live', source: 'whip' });
    toast.success('已开始推流');
  } catch (error) {
    await cleanup();
    const message = error instanceof Error ? error.message : '开播失败';
    errorText.value = message;
    toast.error(message);
  } finally {
    connecting.value = false;
  }
}

async function cleanup() {
  window.clearInterval(compositeTimer);
  window.clearInterval(statsTimer);
  window.clearInterval(clockTimer);
  compositeTimer = 0;
  statsTimer = 0;
  clockTimer = 0;
  await stopWhip(handle);
  handle = null;
  stopStream(stream);
  stopStream(screenStream);
  stopStream(cameraStream);
  stream = null;
  screenStream = null;
  cameraStream = null;
  if (preview.value) preview.value.srcObject = null;
  if (cameraPreview.value) cameraPreview.value.srcObject = null;
  publishing.value = false;
  connectionState.value = '';
}

async function stop() {
  await cleanup();
  emit('changed', { status: 'offline', source: '' });
  toast.success('已结束直播');
}

watch(
  () => props.roomId,
  () => {
    if (publishing.value) void stop();
  },
);

onMounted(() => {
  void loadDevices();
});

onBeforeUnmount(() => {
  if (publishing.value) void cleanup();
});
</script>

<template>
  <div class="space-y-3">
    <p v-if="!allowBrowser" class="surface p-6 text-center text-sm muted">
      管理员关闭了「浏览器开播」，请改用 OBS 推流。
    </p>
    <p v-else-if="!supported" class="surface p-6 text-center text-sm muted">
      浏览器开播需要 HTTPS 或 localhost 环境（浏览器只在安全上下文里允许采集屏幕 / 摄像头）。
    </p>

    <template v-else>
      <div class="grid grid-cols-1 gap-3 lg:grid-cols-[1.5fr_1fr]">
        <!-- 预览 -->
        <div class="space-y-2">
          <div class="player-shell aspect-video bg-black">
            <video ref="preview" class="h-full w-full" muted autoplay playsinline></video>
            <video
              v-if="sourceKind === 'pip'"
              ref="cameraPreview"
              class="absolute bottom-3 right-3 h-[26%] w-[26%] rounded-xl border border-white/60 object-cover"
              muted
              autoplay
              playsinline
            ></video>
            <div v-if="!publishing" class="absolute inset-0 grid place-items-center bg-black/55 text-center text-white">
              <div class="space-y-1.5">
                <Icon name="radio" :size="30" class="mx-auto opacity-80" />
                <p class="text-sm">{{ connecting ? '正在连接推流服务器…' : '预览区（点开始直播后画面会推给观众）' }}</p>
              </div>
            </div>
            <span
              v-if="publishing"
              class="absolute left-3 top-3 flex items-center gap-1.5 rounded-md bg-rose-500 px-2 py-0.5 text-[11px] font-semibold text-white"
            >
              <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-white"></span>直播中 {{ clock(elapsed) }}
            </span>
            <span
              v-else-if="connectionState"
              class="absolute left-3 top-3 rounded-md bg-black/60 px-2 py-0.5 text-[11px] text-white"
            >
              {{ connectionState }}
            </span>
          </div>

          <div v-if="publishing" class="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div class="surface px-3 py-2">
              <p class="text-[10px] muted">上行码率</p>
              <p class="font-mono text-sm font-semibold">{{ mbit(stats.bitrate) }}</p>
            </div>
            <div class="surface px-3 py-2">
              <p class="text-[10px] muted">画面</p>
              <p class="font-mono text-sm font-semibold">{{ stats.width || '—' }}×{{ stats.height || '—' }}</p>
            </div>
            <div class="surface px-3 py-2">
              <p class="text-[10px] muted">帧率</p>
              <p class="font-mono text-sm font-semibold">{{ stats.fps || '—' }} fps</p>
            </div>
            <div class="surface px-3 py-2">
              <p class="text-[10px] muted">丢包</p>
              <p class="font-mono text-sm font-semibold">{{ stats.packetsLost }}</p>
            </div>
          </div>

          <p v-if="errorText" class="rounded-xl bg-rose-500/10 px-3 py-2 text-xs text-rose-500">{{ errorText }}</p>
        </div>

        <!-- 设置 -->
        <div class="space-y-3">
          <div class="surface space-y-2 p-3">
            <p class="text-xs font-semibold">画面来源</p>
            <div class="grid grid-cols-3 gap-1.5">
              <button
                v-for="item in [
                  { key: 'screen', label: '屏幕共享', icon: 'tv', disabled: !canScreen },
                  { key: 'camera', label: '摄像头', icon: 'video', disabled: false },
                  { key: 'pip', label: '画中画', icon: 'sparkles', disabled: !canScreen },
                ]"
                :key="item.key"
                class="flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-[11px] transition disabled:opacity-40"
                :class="sourceKind === item.key ? 'border-[var(--pv-accent)] bg-[var(--pv-accent)]/10 text-[var(--pv-accent)]' : 'border-[var(--pv-border)] muted hover:border-[var(--pv-accent)]/50'"
                :disabled="item.disabled || publishing"
                @click="sourceKind = item.key as SourceKind"
              >
                <Icon :name="item.icon" :size="16" />{{ item.label }}
              </button>
            </div>
            <p class="text-[11px] muted">
              {{ sourceKind === 'screen' ? '共享整个屏幕或某个窗口' : sourceKind === 'camera' ? '使用摄像头画面' : '屏幕为主画面，右下角叠加摄像头' }}
            </p>
          </div>

          <div class="surface space-y-2.5 p-3">
            <p class="text-xs font-semibold">设备与画质</p>
            <div v-if="sourceKind !== 'screen'">
              <label class="label">摄像头</label>
              <select v-model="cameraId" class="input" :disabled="publishing">
                <option v-for="item in cameras" :key="item.deviceId" :value="item.deviceId">
                  {{ item.label || '摄像头' }}
                </option>
              </select>
            </div>
            <div>
              <label class="label">麦克风</label>
              <select v-model="micId" class="input" :disabled="publishing || !audioEnabled">
                <option v-for="item in microphones" :key="item.deviceId" :value="item.deviceId">
                  {{ item.label || '麦克风' }}
                </option>
              </select>
            </div>
            <label class="flex items-center gap-2 text-xs muted">
              <input v-model="audioEnabled" type="checkbox" :disabled="publishing" />采集声音
            </label>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="label">分辨率</label>
                <select v-model.number="resolution" class="input" :disabled="publishing">
                  <option :value="480">480p</option>
                  <option :value="720">720p</option>
                  <option :value="1080">1080p</option>
                </select>
              </div>
              <div>
                <label class="label">帧率</label>
                <select v-model.number="fps" class="input" :disabled="publishing">
                  <option :value="15">15 fps</option>
                  <option :value="24">24 fps</option>
                  <option :value="30">30 fps</option>
                  <option :value="60">60 fps</option>
                </select>
              </div>
            </div>
            <div>
              <label class="label">码率上限（kbps）</label>
              <input v-model.number="bitrate" type="number" class="input" :min="500" :max="Number(studio?.maxBitrate || 6000)" :disabled="publishing" />
              <p class="mt-1 text-[11px] muted">站点上限 {{ studio?.maxBitrate || 6000 }} kbps</p>
            </div>
          </div>

          <button v-if="!publishing" class="btn-primary w-full" :disabled="connecting || !ready" @click="start">
            <Icon name="radio" :size="16" />{{ connecting ? '连接中…' : '开始直播' }}
          </button>
          <button v-else class="btn-danger w-full" @click="stop">
            <Icon name="close" :size="16" />结束直播
          </button>
          <p v-if="!ready" class="text-center text-[11px] text-amber-500">
            推流地址还没配置好，请让管理员检查后台「直播」设置
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
