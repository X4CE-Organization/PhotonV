<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { api } from '../api';
import { useAppStore } from '../store';
import { formatNumber, fromNow } from '../utils';
import VideoCard from '../components/VideoCard.vue';

const store = useAppStore();
const data = ref<any>({ carousel: [], recommend: [], latest: [], ranking: [], rankingByLike: [], featured: [], announcements: [], stats: {} });
const loading = ref(true);
const slide = ref(0);
const tab = ref<'recommend' | 'latest' | 'featured'>('recommend');
let timer = 0;

async function load() {
  loading.value = true;
  try {
    data.value = await api.get<any>('/api/home');
  } finally {
    loading.value = false;
  }
}

function rotate() {
  const total = data.value.carousel?.length || 0;
  if (total > 1) slide.value = (slide.value + 1) % total;
}

onMounted(async () => {
  await load();
  const interval = Math.max(2, Number(store.settings.home_carousel_interval || 5)) * 1000;
  timer = window.setInterval(rotate, interval);
});
onUnmounted(() => window.clearInterval(timer));
</script>

<template>
  <div class="space-y-5">
    <p v-if="data.notice" class="rounded-lg bg-primary/10 px-4 py-2 text-sm text-primary">📢 {{ data.notice }}</p>

    <div class="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <div class="relative overflow-hidden rounded-xl bg-slate-900">
        <template v-if="data.carousel?.length">
          <RouterLink :to="data.carousel[slide]?.link || '/'" class="block">
            <img :src="data.carousel[slide].image" :alt="data.carousel[slide].title" class="aspect-[16/7] w-full object-cover opacity-90" />
            <div class="absolute bottom-4 left-5 text-white">
              <h2 class="text-xl font-bold drop-shadow">{{ data.carousel[slide].title }}</h2>
              <p class="mt-1 text-sm opacity-90">{{ data.carousel[slide].subtitle }}</p>
            </div>
          </RouterLink>
          <div class="absolute bottom-3 right-4 flex gap-1.5">
            <button
              v-for="(item, index) in data.carousel"
              :key="item.id"
              class="h-1.5 w-5 rounded-full transition"
              :class="index === slide ? 'bg-white' : 'bg-white/40'"
              @click.prevent="slide = index"
            ></button>
          </div>
        </template>
        <div v-else class="grid aspect-[16/7] place-items-center text-slate-500">还没有轮播内容</div>
      </div>

      <div class="card p-4">
        <h3 class="text-sm font-semibold">社区数据</h3>
        <div class="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div><div class="text-xl font-bold text-primary">{{ formatNumber(data.stats.users) }}</div><div class="text-xs text-slate-400">注册用户</div></div>
          <div><div class="text-xl font-bold text-primary">{{ formatNumber(data.stats.videos) }}</div><div class="text-xs text-slate-400">公开视频</div></div>
          <div><div class="text-xl font-bold text-primary">{{ formatNumber(data.stats.views) }}</div><div class="text-xs text-slate-400">总播放</div></div>
          <div><div class="text-xl font-bold text-primary">{{ formatNumber(data.stats.danmaku) }}</div><div class="text-xs text-slate-400">弹幕总数</div></div>
        </div>
        <RouterLink to="/rank" class="btn-ghost mt-4 w-full text-xs">查看完整排行榜</RouterLink>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <div class="mb-3 flex items-center gap-3 text-sm">
          <button :class="tab === 'recommend' ? 'font-semibold text-primary' : 'text-slate-500'" @click="tab = 'recommend'">推荐</button>
          <button :class="tab === 'latest' ? 'font-semibold text-primary' : 'text-slate-500'" @click="tab = 'latest'">最新</button>
          <button :class="tab === 'featured' ? 'font-semibold text-primary' : 'text-slate-500'" @click="tab = 'featured'">精选</button>
        </div>
        <p v-if="loading" class="py-10 text-center text-sm text-slate-400">加载中…</p>
        <div v-else-if="!(data[tab] || []).length" class="card p-10 text-center text-sm text-slate-400">
          还没有视频，登录后点击右上角「投稿」发布第一条吧
        </div>
        <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
          <VideoCard v-for="video in data[tab]" :key="video.id" :video="video" />
        </div>
      </div>

      <aside class="space-y-4">
        <div v-if="store.settings.show_home_ranking !== false" class="card p-4">
          <h3 class="mb-3 text-sm font-semibold">🔥 热门排行</h3>
          <ol class="space-y-2">
            <li v-for="(video, index) in data.ranking" :key="video.id" class="flex gap-2 text-sm">
              <span class="w-4 shrink-0 text-center text-xs font-semibold" :class="index < 3 ? 'text-primary' : 'text-slate-400'">{{ index + 1 }}</span>
              <RouterLink :to="`/video/${video.id}`" class="line-clamp-2 flex-1 hover:text-primary">{{ video.title }}</RouterLink>
              <span class="shrink-0 text-xs text-slate-400">{{ formatNumber(video.views) }}</span>
            </li>
          </ol>
        </div>

        <div class="card p-4">
          <h3 class="mb-3 text-sm font-semibold">📢 公告</h3>
          <ul class="space-y-2 text-sm">
            <li v-for="item in data.announcements" :key="item.id">
              <div class="font-medium">{{ item.title }}</div>
              <p class="mt-0.5 line-clamp-2 text-xs text-slate-500">{{ item.content }}</p>
              <div class="mt-0.5 text-[11px] text-slate-400">{{ fromNow(item.createdAt) }}</div>
            </li>
            <li v-if="!data.announcements?.length" class="text-xs text-slate-400">暂无公告</li>
          </ul>
        </div>

        <div class="card p-4">
          <h3 class="mb-3 text-sm font-semibold">🏷 热门标签</h3>
          <div class="flex flex-wrap gap-2">
            <RouterLink
              v-for="item in store.hotTags"
              :key="item.id"
              :to="`/search?q=${encodeURIComponent(item.name)}`"
              class="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 hover:bg-primary/10 hover:text-primary dark:bg-slate-800 dark:text-slate-300"
            >
              {{ item.name }}
            </RouterLink>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
