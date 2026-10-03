<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';
import Icon from '../../components/Icon.vue';

const data = ref<any>(null);
const busy = ref(false);
let timer = 0;

async function load() {
  try {
    data.value = await api.get<any>('/api/admin/infra');
  } catch {
    /* ignore */
  }
}

async function clearCache() {
  busy.value = true;
  try {
    const result = await api.post<any>('/api/admin/cache/clear');
    toast.success(`已清理 ${result.removed} 个缓存键`);
  } finally {
    busy.value = false;
  }
}

async function retranscodeAll() {
  busy.value = true;
  try {
    const videos = await api.get<any>('/api/admin/videos?size=50');
    let count = 0;
    for (const video of videos.items || []) {
      if (video.status === 'published') {
        await api.post(`/api/admin/videos/${video.id}/transcode`);
        count += 1;
      }
    }
    toast.success(`已重新加入转码队列 ${count} 个视频`);
    void load();
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  void load();
  timer = window.setInterval(load, 10000);
});
onUnmounted(() => window.clearInterval(timer));
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-base font-semibold">缓存与转码</h1>
      <button class="btn-ghost text-xs" :disabled="busy" @click="load"><Icon name="refresh" :size="15" />刷新</button>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="surface p-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="server" :size="16" />Redis</h2>
        <dl class="mt-3 space-y-2 text-sm">
          <div class="flex justify-between"><dt class="muted">状态</dt>
            <dd :class="data?.redis?.connected ? 'text-emerald-500' : 'text-amber-500'">
              {{ data?.redis?.connected ? '已连接' : data?.redis?.enabled ? '未连接' : '未配置' }}
            </dd>
          </div>
          <div class="flex justify-between"><dt class="muted">版本</dt><dd>{{ data?.redis?.version || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="muted">内存占用</dt><dd>{{ data?.redis?.memory || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="muted">键数量</dt><dd>{{ data?.redis?.keys ?? '—' }}</dd></div>
          <div class="flex justify-between"><dt class="muted">在线用户</dt><dd>{{ data?.redis?.online ?? 0 }}</dd></div>
          <div v-if="data?.redis?.error" class="text-xs text-amber-500">{{ data.redis.error }}</div>
        </dl>
        <button class="btn-ghost mt-3 text-xs" :disabled="busy" @click="clearCache">清理缓存</button>
      </section>

      <section class="surface p-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="film" :size="16" />ffmpeg 转码</h2>
        <dl class="mt-3 space-y-2 text-sm">
          <div class="flex justify-between"><dt class="muted">可用</dt>
            <dd :class="data?.ffmpeg?.available ? 'text-emerald-500' : 'text-amber-500'">{{ data?.ffmpeg?.available ? '是' : '否' }}</dd>
          </div>
          <div class="flex justify-between"><dt class="muted">路径</dt><dd class="max-w-[60%] truncate text-xs">{{ data?.ffmpeg?.path || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="muted">版本</dt><dd class="max-w-[60%] truncate text-xs">{{ data?.ffmpeg?.version || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="muted">清晰度文件</dt><dd>{{ data?.variants ?? 0 }} 个</dd></div>
        </dl>
        <div class="mt-3 grid grid-cols-5 gap-2 text-center text-xs">
          <div><div class="text-lg font-bold">{{ data?.transcode?.pending ?? 0 }}</div><div class="muted">排队</div></div>
          <div><div class="text-lg font-bold text-amber-500">{{ data?.transcode?.processing ?? 0 }}</div><div class="muted">转码中</div></div>
          <div><div class="text-lg font-bold text-emerald-500">{{ data?.transcode?.done ?? 0 }}</div><div class="muted">完成</div></div>
          <div><div class="text-lg font-bold text-rose-500">{{ data?.transcode?.failed ?? 0 }}</div><div class="muted">失败</div></div>
          <div><div class="text-lg font-bold muted">{{ data?.transcode?.skipped ?? 0 }}</div><div class="muted">跳过</div></div>
        </div>
        <button class="btn-primary mt-3 text-xs" :disabled="busy" @click="retranscodeAll">重新转码最近 50 个视频</button>
      </section>

      <section class="surface p-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="zap" :size="16" />实时连接</h2>
        <dl class="mt-3 space-y-2 text-sm">
          <div class="flex justify-between"><dt class="muted">房间数</dt><dd>{{ data?.realtime?.rooms ?? 0 }}</dd></div>
          <div class="flex justify-between"><dt class="muted">连接数</dt><dd>{{ data?.realtime?.connections ?? 0 }}</dd></div>
        </dl>
        <p class="mt-3 text-xs muted">
          私信与直播聊天走 WebSocket；配置 Redis 后消息会通过 Pub/Sub 在多个进程之间同步，
          所以可以直接开多个副本做负载均衡。
        </p>
      </section>

      <section class="surface p-4 text-xs muted">
        <h2 class="mb-2 text-sm font-semibold text-[var(--pv-text)]">部署提示</h2>
        <p>1. 服务器安装 ffmpeg（<code>apt install ffmpeg</code>），或设置 <code>FFMPEG_BIN</code> 指向二进制。</p>
        <p class="mt-1">2. 设置 <code>REDIS_URL=redis://127.0.0.1:6379</code> 开启缓存与分布式限流。</p>
        <p class="mt-1">3. 多副本部署时记得把 <code>DATA_DIR</code> 挂到共享存储（对象存储或 NFS）。</p>
      </section>
    </div>
  </div>
</template>
