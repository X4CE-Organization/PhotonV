<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';

const route = useRoute();
const store = useAppStore();
const data = ref<any>(null);
const level = ref<any>(null);
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(24);
const tab = ref('videos');
const status = ref('all');
const following = ref(false);
const loading = ref(true);
const follows = ref<any[]>([]);

async function load() {
  loading.value = true;
  try {
    const username = String(route.params.username);
    const [profile, videos] = await Promise.all([
      api.get<any>(`/api/users/${username}`),
      api.get<any>(`/api/users/${username}/videos${query({ page: page.value, status: status.value || 'published' })}`),
    ]);
    data.value = profile.profile;
    level.value = profile.level;
    following.value = profile.isFollowing;
    items.value = videos.items || [];
    total.value = videos.total || 0;
    size.value = videos.size || 24;
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '用户不存在');
  } finally {
    loading.value = false;
  }
}

async function loadFollows(kind: 'followers' | 'following') {
  const username = String(route.params.username);
  const result = await api.get<any>(`/api/users/${username}/${kind}${query({ size: 60 })}`);
  follows.value = result.items || [];
}

function switchTab(value: string) {
  tab.value = value;
  if (value === 'followers') void loadFollows('followers');
  else if (value === 'following') void loadFollows('following');
}

async function toggleFollow() {
  if (!store.isLogin) return toast.info('请先登录');
  const result = await api.post<any>(`/api/users/${route.params.username}/follow`);
  following.value = result.following;
  if (data.value) data.value.followers = result.followers;
}

function isSelf() {
  return store.user?.username === String(route.params.username);
}

watch(() => route.params.username, () => {
  page.value = 1;
  tab.value = 'videos';
  void load();
});
onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中…</p>
  <div v-else-if="data" class="space-y-4">
    <div class="card overflow-hidden">
      <div
        class="h-32 bg-gradient-to-r from-primary/60 to-indigo-500/60"
        :style="data.banner ? { backgroundImage: `url(${data.banner})`, backgroundSize: 'cover', backgroundPosition: 'center' } : {}"
      ></div>
      <div class="flex flex-wrap items-end gap-4 px-4 pb-4">
        <img
          v-if="data.avatar"
          :src="data.avatar"
          class="-mt-10 h-20 w-20 rounded-full border-4 border-white object-cover dark:border-slate-900"
          alt=""
        />
        <span
          v-else
          class="-mt-10 grid h-20 w-20 place-items-center rounded-full border-4 border-white bg-primary/15 text-2xl font-semibold text-primary dark:border-slate-900"
        >
          {{ initials(data.displayName) }}
        </span>
        <div class="flex-1">
          <h1 class="text-lg font-semibold">{{ data.displayName }}</h1>
          <p class="text-xs text-slate-400">@{{ data.username }} · 加入于 {{ fromNow(data.joinedAt) }}</p>
          <p class="mt-1 text-sm text-slate-500">{{ data.bio || '这个人很神秘，什么都没写' }}</p>
        </div>
        <div class="flex gap-2">
          <RouterLink v-if="isSelf()" to="/settings" class="btn-ghost">编辑资料</RouterLink>
          <button v-else class="btn-primary" @click="toggleFollow">{{ following ? '已关注' : '+ 关注' }}</button>
        </div>
      </div>
      <div class="flex flex-wrap gap-6 border-t border-slate-100 px-4 py-3 text-sm dark:border-slate-800">
        <button class="hover:text-primary" @click="switchTab('videos')"><b>{{ data.videoCount }}</b> <span class="text-xs text-slate-400">投稿</span></button>
        <button class="hover:text-primary" @click="switchTab('followers')"><b>{{ data.followers }}</b> <span class="text-xs text-slate-400">粉丝</span></button>
        <button class="hover:text-primary" @click="switchTab('following')"><b>{{ data.following }}</b> <span class="text-xs text-slate-400">关注</span></button>
        <span><b>{{ formatNumber(data.playCount) }}</b> <span class="text-xs text-slate-400">总播放</span></span>
        <span><b>{{ formatNumber(data.likeCount) }}</b> <span class="text-xs text-slate-400">获赞</span></span>
        <span v-if="level" class="ml-auto text-xs text-slate-400">
          {{ level.name }} · {{ level.current }}/{{ level.next }} 经验
        </span>
      </div>
    </div>

    <template v-if="tab === 'videos'">
      <div v-if="isSelf()" class="flex flex-wrap gap-2 text-sm">
        <button
          v-for="item in [
            { key: 'all', label: '全部' },
            { key: 'published', label: '已公开' },
            { key: 'pending', label: '审核中' },
            { key: 'rejected', label: '未通过' },
            { key: 'private', label: '仅自己' },
          ]"
          :key="item.key"
          class="rounded-lg px-3 py-1.5"
          :class="status === item.key ? 'bg-primary/10 font-medium text-primary' : 'text-slate-500'"
          @click="status = item.key; page = 1; load()"
        >
          {{ item.label }}
        </button>
      </div>

      <p v-if="!items.length" class="card p-16 text-center text-sm text-slate-400">还没有投稿</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in items" :key="video.id" :video="video" />
      </div>
      <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
    </template>

    <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <RouterLink
        v-for="user in follows"
        :key="user.id"
        :to="`/space/${user.username}`"
        class="card flex items-center gap-3 p-3 hover:shadow-md"
      >
        <img v-if="user.avatar" :src="user.avatar" class="h-11 w-11 rounded-full object-cover" alt="" />
        <span v-else class="grid h-11 w-11 place-items-center rounded-full bg-primary/15 font-semibold text-primary">
          {{ initials(user.displayName) }}
        </span>
        <div class="min-w-0">
          <div class="text-sm font-medium">{{ user.displayName }}</div>
          <p class="text-xs text-slate-400">{{ formatNumber(user.followerCount) }} 粉丝</p>
        </div>
      </RouterLink>
      <p v-if="!follows.length" class="col-span-full py-10 text-center text-sm text-slate-400">暂无数据</p>
    </div>
  </div>
</template>
