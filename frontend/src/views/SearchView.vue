<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { api, query } from '../api';
import { formatNumber, initials } from '../utils';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';

const route = useRoute();
const router = useRouter();
const keyword = ref(String(route.query.q || ''));
const tab = ref<'video' | 'user'>('video');
const videos = ref<any[]>([]);
const users = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(24);
const loading = ref(false);

async function load() {
  if (!keyword.value.trim()) return;
  loading.value = true;
  try {
    const data = await api.get<any>(
      `/api/search${query({ q: keyword.value.trim(), type: tab.value, page: page.value })}`,
    );
    videos.value = data.videos || [];
    users.value = data.users || [];
    total.value = data.total || 0;
    size.value = data.size || 24;
  } finally {
    loading.value = false;
  }
}

function submit() {
  router.replace({ name: 'search', query: { q: keyword.value.trim() } });
  page.value = 1;
  void load();
}

watch(() => route.query.q, (value) => {
  keyword.value = String(value || '');
  page.value = 1;
  void load();
});

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <form class="card flex gap-2 p-3" @submit.prevent="submit">
      <input v-model="keyword" class="input flex-1" placeholder="搜索视频、用户" />
      <button class="btn-primary">搜索</button>
    </form>

    <div class="flex gap-4 text-sm">
      <button :class="tab === 'video' ? 'font-semibold text-primary' : 'text-slate-500'" @click="tab = 'video'; load()">视频</button>
      <button :class="tab === 'user' ? 'font-semibold text-primary' : 'text-slate-500'" @click="tab = 'user'; load()">用户</button>
    </div>

    <p v-if="loading" class="py-16 text-center text-sm text-slate-400">搜索中…</p>

    <template v-else-if="tab === 'video'">
      <p v-if="!videos.length" class="card p-16 text-center text-sm text-slate-400">没有找到相关视频</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in videos" :key="video.id" :video="video" />
      </div>
      <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
    </template>

    <template v-else>
      <p v-if="!users.length" class="card p-16 text-center text-sm text-slate-400">没有找到相关用户</p>
      <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <RouterLink
          v-for="user in users"
          :key="user.id"
          :to="`/space/${user.username}`"
          class="card flex items-center gap-3 p-3 hover:shadow-md"
        >
          <img v-if="user.avatar" :src="user.avatar" class="h-12 w-12 rounded-full object-cover" alt="" />
          <span v-else class="grid h-12 w-12 place-items-center rounded-full bg-primary/15 font-semibold text-primary">
            {{ initials(user.displayName) }}
          </span>
          <div class="min-w-0">
            <div class="font-medium">{{ user.displayName }}</div>
            <p class="line-clamp-1 text-xs text-slate-500">{{ user.bio || '这个人很神秘' }}</p>
            <p class="mt-0.5 text-[11px] text-slate-400">{{ formatNumber(user.followerCount) }} 粉丝 · {{ user.videoCount }} 投稿</p>
          </div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>
