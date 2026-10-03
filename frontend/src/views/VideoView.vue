<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import DanmakuPlayer from '../components/DanmakuPlayer.vue';
import CommentList from '../components/CommentList.vue';

const route = useRoute();
const store = useAppStore();
const video = ref<any>(null);
const danmaku = ref<any[]>([]);
const allowDanmaku = ref(true);
const related = ref<any[]>([]);
const loading = ref(true);
const folders = ref<any[]>([]);
const showFolders = ref(false);
const following = ref(false);
const showReport = ref(false);
const reportReason = ref('spam');
const reportDetail = ref('');
const reasons = computed(() => store.settings.report_reasons || []);

async function load() {
  loading.value = true;
  try {
    video.value = await api.get<any>(`/api/videos/${route.params.id}`);
    const [danmakuData, relatedData] = await Promise.all([
      api.get<any>(`/api/videos/${route.params.id}/danmaku`),
      api.get<any>(`/api/videos/${route.params.id}/related`),
    ]);
    danmaku.value = danmakuData.items || [];
    allowDanmaku.value = Boolean(danmakuData.allowDanmaku);
    related.value = relatedData.items || [];
    if (store.isLogin) {
      const data = await api.get<any>(`/api/users/${video.value.author.username}`);
      following.value = Boolean(data.isFollowing);
      const favs = await api.get<any>('/api/me/favorite-folders');
      folders.value = favs.items || [];
    }
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '视频不存在');
  } finally {
    loading.value = false;
  }
}

function requireLogin(): boolean {
  if (!store.isLogin) {
    toast.info('请先登录');
    return false;
  }
  return true;
}

async function toggleLike() {
  if (!requireLogin()) return;
  const data = await api.post<any>(`/api/videos/${video.value.id}/like`);
  video.value.liked = data.liked;
  video.value.likes = data.likes;
}

async function giveCoin() {
  if (!requireLogin()) return;
  try {
    const data = await api.post<any>(`/api/videos/${video.value.id}/coin`, { amount: 1 });
    video.value.coined = true;
    video.value.coins = data.coins;
    if (store.user) store.user.coins = data.myCoins;
    toast.success('投币成功');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '投币失败');
  }
}

async function favorite(folderId?: number) {
  if (!requireLogin()) return;
  const data = await api.post<any>(`/api/videos/${video.value.id}/favorite`, { folder_id: folderId });
  video.value.favorited = data.favorited;
  video.value.favorites = data.favorites;
  showFolders.value = false;
  toast.success(data.favorited ? '已收藏' : '已取消收藏');
}

async function toggleFollow() {
  if (!requireLogin()) return;
  const data = await api.post<any>(`/api/users/${video.value.author.username}/follow`);
  following.value = data.following;
}

async function share() {
  const url = `${location.origin}/video/${video.value.id}`;
  try {
    await navigator.clipboard.writeText(url);
    toast.success('链接已复制');
  } catch {
    toast.info(url);
  }
  void api.post(`/api/videos/${video.value.id}/share`).catch(() => undefined);
}

async function report() {
  if (!requireLogin()) return;
  try {
    await api.post('/api/reports', {
      target_type: 'video',
      target_id: video.value.id,
      reason: reportReason.value,
      detail: reportDetail.value,
    });
    showReport.value = false;
    reportDetail.value = '';
    toast.success('举报已提交，管理员会尽快处理');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '举报失败');
  }
}

onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中…</p>
  <div v-else-if="video" class="grid gap-5 lg:grid-cols-[1fr_320px]">
    <div>
      <DanmakuPlayer
        :video="video"
        :danmaku="danmaku"
        :allow-danmaku="allowDanmaku"
        @sent="(item) => danmaku.push(item)"
      />

      <h1 class="mt-4 text-lg font-semibold">{{ video.title }}</h1>
      <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-400">
        <span>▶ {{ formatNumber(video.views) }} 播放</span>
        <span>💬 {{ formatNumber(video.comments) }} 评论</span>
        <span>💭 {{ formatNumber(video.danmaku) }} 弹幕</span>
        <span>{{ fromNow(video.publishedAt || video.createdAt) }}</span>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <button class="btn-ghost" :class="video.liked ? '!text-rose-500' : ''" @click="toggleLike">👍 {{ video.likes }}</button>
        <button class="btn-ghost" :disabled="video.coined" @click="giveCoin">🪙 {{ video.coins }}</button>
        <div class="relative">
          <button class="btn-ghost" @click="showFolders = !showFolders">⭐ {{ video.favorites }}</button>
          <div v-if="showFolders" class="absolute left-0 top-full z-20 mt-1 w-44 rounded-lg border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <button class="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800" @click="favorite()">默认收藏夹</button>
            <button
              v-for="folder in folders.filter((item) => !item.isDefault)"
              :key="folder.id"
              class="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
              @click="favorite(folder.id)"
            >
              {{ folder.name }}
            </button>
          </div>
        </div>
        <button class="btn-ghost" @click="share">🔗 分享</button>
        <button v-if="store.settings.allow_report !== false" class="btn-ghost" @click="showReport = true">⚑ 举报</button>
      </div>

      <div class="card mt-4 p-4">
        <div class="flex items-start gap-3">
          <RouterLink :to="`/space/${video.author.username}`" class="shrink-0">
            <img v-if="video.author.avatar" :src="video.author.avatar" class="h-11 w-11 rounded-full object-cover" alt="" />
            <span v-else class="grid h-11 w-11 place-items-center rounded-full bg-primary/15 font-semibold text-primary">
              {{ initials(video.author.displayName) }}
            </span>
          </RouterLink>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <RouterLink :to="`/space/${video.author.username}`" class="font-medium hover:text-primary">{{ video.author.displayName }}</RouterLink>
              <span class="rounded bg-slate-100 px-1.5 text-[11px] text-slate-500 dark:bg-slate-800">Lv{{ video.author.level }}</span>
              <span class="text-xs text-slate-400">{{ formatNumber(video.author.followerCount) }} 粉丝</span>
            </div>
            <p class="mt-1 line-clamp-2 text-xs text-slate-500">{{ video.author.bio || '这个人很神秘，什么都没写' }}</p>
          </div>
          <button v-if="!video.canEdit" class="btn-primary shrink-0" @click="toggleFollow">
            {{ following ? '已关注' : '+ 关注' }}
          </button>
          <RouterLink v-else to="/upload" class="btn-ghost shrink-0">投稿管理</RouterLink>
        </div>

        <div class="mt-3 whitespace-pre-wrap border-t border-slate-100 pt-3 text-sm leading-relaxed dark:border-slate-800">
          {{ video.description || '这个 UP 主很懒，什么都没写' }}
        </div>

        <div v-if="video.tags?.length || video.category" class="mt-3 flex flex-wrap gap-2">
          <RouterLink
            v-if="video.category"
            :to="`/category/${video.category.slug}`"
            class="rounded-full bg-primary/10 px-2.5 py-1 text-xs text-primary"
          >
            {{ video.category.name }}
          </RouterLink>
          <RouterLink
            v-for="tag in video.tags"
            :key="tag.id"
            :to="`/search?q=${encodeURIComponent(tag.name)}`"
            class="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 hover:bg-primary/10 hover:text-primary dark:bg-slate-800 dark:text-slate-300"
          >
            # {{ tag.name }}
          </RouterLink>
        </div>
      </div>

      <CommentList :video-id="video.id" :allow-comment="Boolean(video.allowComment)" />
    </div>

    <aside class="space-y-3">
      <h3 class="text-sm font-semibold">相关推荐</h3>
      <RouterLink
        v-for="item in related"
        :key="item.id"
        :to="`/video/${item.id}`"
        class="flex gap-2 rounded-lg p-1.5 transition hover:bg-slate-100 dark:hover:bg-slate-800"
      >
        <img :src="item.cover" class="h-14 w-24 shrink-0 rounded object-cover" alt="" />
        <div class="min-w-0">
          <p class="line-clamp-2 text-xs font-medium">{{ item.title }}</p>
          <p class="mt-1 text-[11px] text-slate-400">{{ item.author.displayName }} · {{ formatNumber(item.views) }} 播放</p>
        </div>
      </RouterLink>
      <p v-if="!related.length" class="text-xs text-slate-400">暂无相关推荐</p>
    </aside>

    <div v-if="showReport" class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" @click.self="showReport = false">
      <div class="w-full max-w-md rounded-xl bg-white p-4 dark:bg-slate-900">
        <h3 class="text-sm font-semibold">举报视频</h3>
        <select v-model="reportReason" class="input mt-3">
          <option v-for="item in reasons" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <textarea v-model="reportDetail" class="input mt-2 min-h-[80px]" placeholder="补充说明（可选）"></textarea>
        <div class="mt-3 flex justify-end gap-2">
          <button class="btn-ghost" @click="showReport = false">取消</button>
          <button class="btn-primary" @click="report">提交举报</button>
        </div>
      </div>
    </div>
  </div>
</template>
