<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import Icon from '../components/Icon.vue';

const route = useRoute();
const store = useAppStore();
const playlist = ref<any>(null);
const items = ref<any[]>([]);
const loading = ref(true);
const currentIndex = ref(0);

const current = computed(() => items.value[currentIndex.value] || null);

function clock(seconds: number): string {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/playlists/${route.params.id}`);
    playlist.value = data.playlist;
    items.value = data.items || [];
    currentIndex.value = 0;
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '合集不存在');
    playlist.value = null;
  } finally {
    loading.value = false;
  }
}

async function removeItem(video: any) {
  if (!window.confirm(`把《${video.title}》从这个合集里移除？`)) return;
  try {
    await api.del(`/api/playlists/${playlist.value.id}/items/${video.id}`);
    toast.success('已移除');
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '移除失败');
  }
}

watch(() => route.params.id, load);
onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <div v-else-if="playlist" class="space-y-4">
    <div class="surface flex flex-wrap items-center gap-4 p-4">
      <img v-if="playlist.cover" :src="playlist.cover" class="h-24 w-40 rounded-2xl object-cover" alt="" />
      <div v-else class="grid h-24 w-40 shrink-0 place-items-center rounded-2xl bg-[var(--pv-surface-2)] text-xs muted">暂无封面</div>
      <div class="min-w-0 flex-1">
        <h1 class="flex items-center gap-2 text-lg font-semibold">
          <Icon name="list" :size="18" />{{ playlist.title }}
        </h1>
        <p class="mt-1 line-clamp-2 text-xs muted">{{ playlist.description || '这个合集还没有简介' }}</p>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs muted">
          <RouterLink v-if="playlist.owner" :to="`/space/${playlist.owner.username}`" class="flex items-center gap-1 hover:text-[var(--pv-accent)]">
            <img v-if="playlist.owner.avatar" :src="playlist.owner.avatar" class="h-5 w-5 rounded-full object-cover" alt="" />
            <span v-else class="grid h-5 w-5 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-[10px] font-bold text-white">
              {{ initials(playlist.owner.displayName) }}
            </span>
            {{ playlist.owner.displayName }}
          </RouterLink>
          <span>{{ formatNumber(items.length) }} 个视频</span>
          <span class="chip !py-0 text-[10px]">{{ playlist.isPublic ? '公开' : '私有' }}</span>
          <span v-if="playlist.createdAt">{{ fromNow(playlist.createdAt) }} 创建</span>
        </div>
      </div>
      <RouterLink v-if="playlist.isMine" to="/playlists" class="btn-ghost text-xs">管理合集</RouterLink>
    </div>

    <div v-if="!items.length" class="surface p-16 text-center text-sm muted">这个合集还没有视频</div>
    <div v-else class="grid gap-4 lg:grid-cols-[1fr_330px]">
      <div class="space-y-3">
        <div v-if="current" class="surface overflow-hidden">
          <div class="aspect-video w-full bg-black">
            <video
              :key="current.id"
              class="h-full w-full"
              :src="current.sourceUrl || current.source || ''"
              :poster="current.cover"
              controls
              autoplay
              playsinline
            />
          </div>
          <div class="p-3">
            <h2 class="font-medium">{{ current.title }}</h2>
            <div class="mt-1 flex flex-wrap items-center gap-3 text-xs muted">
              <span>{{ formatNumber(current.views) }} 播放</span>
              <span>{{ formatNumber(current.likes) }} 点赞</span>
              <span>{{ clock(current.duration) }}</span>
              <RouterLink :to="`/video/${current.id}`" class="link">去视频页 →</RouterLink>
            </div>
          </div>
        </div>
        <p v-if="!current.sourceUrl && !current.source" class="text-xs muted">该视频没有可直接播放的源文件</p>
      </div>

      <aside class="space-y-2">
        <h3 class="text-sm font-semibold">合集列表（{{ items.length }}）</h3>
        <div class="max-h-[520px] space-y-1 overflow-y-auto pr-1">
          <div
            v-for="(item, index) in items"
            :key="item.id"
            class="group flex cursor-pointer gap-2 rounded-2xl p-1.5 transition"
            :class="index === currentIndex ? 'bg-[var(--pv-surface-2)]' : 'hover:bg-[var(--pv-surface-2)]'"
            @click="currentIndex = index"
          >
            <span class="w-5 shrink-0 text-center text-xs muted">{{ index + 1 }}</span>
            <img :src="item.cover" class="h-12 w-20 shrink-0 rounded-lg object-cover" alt="" />
            <div class="min-w-0 flex-1">
              <p class="line-clamp-2 text-xs font-medium">{{ item.title }}</p>
              <p class="mt-0.5 text-[11px] muted">{{ item.author?.displayName }} · {{ clock(item.duration) }}</p>
            </div>
            <button
              v-if="playlist.isMine"
              class="hidden shrink-0 self-start text-[11px] text-rose-500 group-hover:block"
              @click.stop="removeItem(item)"
            >
              移除
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
  <div v-else class="py-20 text-center text-sm muted">
    合集不存在或没有访问权限
    <RouterLink to="/" class="link ml-1">回首页</RouterLink>
  </div>
</template>
