<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import DanmakuPlayer from '../components/DanmakuPlayer.vue';
import CommentList from '../components/CommentList.vue';
import Icon from '../components/Icon.vue';

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
const showCharge = ref(false);
const chargeCoins = ref(50);
const quality = ref('auto');
const player = ref<any>(null);
const panel = ref<'comments' | 'notes'>('comments');
const notes = ref<any[]>([]);
const noteDraft = ref('');
const notePublic = ref(true);
const notesEnabled = ref(true);
const playlists = ref<any[]>([]);
const showPlaylists = ref(false);

const notesOpen = computed(() => store.settings.video_notes_enabled !== false);

function clock(seconds: number): string {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

const reasons = computed(() => (Array.isArray(store.settings.report_reasons) ? store.settings.report_reasons : []));
const variants = computed(() => video.value?.variants || []);

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
    if (store.isLogin && video.value?.author?.username) {
      const profile = await api.get<any>(`/api/users/${video.value.author.username}`);
      following.value = Boolean(profile.isFollowing);
      const favs = await api.get<any>('/api/me/favorite-folders');
      folders.value = favs.items || [];
      void loadPlaylists();
      void loadNotes();
    }
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '视频不存在');
  } finally {
    loading.value = false;
  }
}

async function loadNotes() {
  try {
    const data = await api.get<any>(`/api/videos/${route.params.id}/notes`);
    notes.value = data.items || [];
    notesEnabled.value = data.enabled !== false;
  } catch {
    notes.value = [];
  }
}

async function loadPlaylists() {
  try {
    const data = await api.get<any>(`/api/playlists/with-video/${route.params.id}`);
    playlists.value = data.items || [];
  } catch {
    playlists.value = [];
  }
}

async function togglePlaylist(item: any) {
  if (!requireLogin()) return;
  try {
    if (item.contains) {
      await api.del(`/api/playlists/${item.id}/items/${video.value.id}`);
      item.contains = false;
      item.videoCount = Math.max(0, (item.videoCount || 1) - 1);
      toast.success('已从合集移除');
    } else {
      await api.post(`/api/playlists/${item.id}/items`, { video_id: video.value.id });
      item.contains = true;
      item.videoCount = (item.videoCount || 0) + 1;
      toast.success(`已加入《${item.title}》`);
    }
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

async function jumpTo(seconds: number) {
  player.value?.seekTo?.(Number(seconds) || 0);
}

async function saveNote() {
  if (!requireLogin()) return;
  const content = noteDraft.value.trim();
  if (!content) return;
  try {
    const data = await api.post<any>(`/api/videos/${route.params.id}/notes`, {
      content,
      time: Number(player.value?.position?.() || 0),
      is_public: notePublic.value,
    });
    notes.value = [...notes.value, data.note].sort((a, b) => a.time - b.time);
    noteDraft.value = '';
    toast.success('笔记已保存');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function removeNote(item: any) {
  try {
    await api.del(`/api/notes/${item.id}`);
    notes.value = notes.value.filter((row) => row.id !== item.id);
    toast.success('已删除');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  }
}

async function toggleNotePublic(item: any) {
  try {
    const data = await api.put<any>(`/api/notes/${item.id}`, { is_public: !item.isPublic });
    item.isPublic = data.note.isPublic;
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '修改失败');
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
  toast.success(data.following ? '已关注' : '已取消关注');
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
    toast.success('举报已提交');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '举报失败');
  }
}

async function charge() {
  if (!requireLogin()) return;
  try {
    await api.post('/api/orders', {
      type: 'charge',
      username: video.value.author.username,
      coins: Number(chargeCoins.value) || 0,
    });
    showCharge.value = false;
    toast.success('充电成功，感谢支持创作者');
    if (store.user) store.user.coins = Math.max(0, (store.user.coins || 0) - Number(chargeCoins.value));
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '充电失败');
  }
}

function switchQuality(value: string) {
  quality.value = value;
}

onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <div v-else-if="video" class="grid gap-4 lg:grid-cols-[1fr_330px]">
    <div class="space-y-4">
      <DanmakuPlayer
        ref="player"
        :video="video"
        :danmaku="danmaku"
        :allow-danmaku="allowDanmaku"
        :quality="quality"
        :variants="variants"
        @sent="(item) => danmaku.push(item)"
        @quality="switchQuality"
      />

      <div class="surface p-4">
        <h1 class="text-lg font-semibold">{{ video.title }}</h1>
        <div class="mt-1.5 flex flex-wrap items-center gap-3 text-xs muted">
          <span class="inline-flex items-center gap-1"><Icon name="play" :size="13" />{{ formatNumber(video.views) }} 播放</span>
          <span class="inline-flex items-center gap-1"><Icon name="message" :size="13" />{{ formatNumber(video.comments) }} 评论</span>
          <span class="inline-flex items-center gap-1"><Icon name="zap" :size="13" />{{ formatNumber(video.danmaku) }} 弹幕</span>
          <span>{{ fromNow(video.publishedAt || video.createdAt) }}</span>
          <span v-if="video.transcodeStatus === 'processing'" class="chip !text-[10px]">转码中</span>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <button class="btn-ghost" :class="video.liked ? '!text-rose-500 !border-rose-500/40' : ''" @click="toggleLike">
            <Icon name="heart" :size="16" />{{ video.likes }}
          </button>
          <button class="btn-ghost" :disabled="video.coined" @click="giveCoin">
            <Icon name="coin" :size="16" />{{ video.coins }}
          </button>
          <div class="relative">
            <button class="btn-ghost" :class="video.favorited ? '!text-amber-500 !border-amber-500/40' : ''" @click="showFolders = !showFolders">
              <Icon name="star" :size="16" />{{ video.favorites }}
            </button>
            <div v-if="showFolders" class="absolute left-0 top-full z-20 mt-1 w-48 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-1.5">
              <button class="block w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-[var(--pv-surface-2)]" @click="favorite()">
                默认收藏夹
              </button>
              <button
                v-for="folder in folders.filter((item) => !item.isDefault)"
                :key="folder.id"
                class="block w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-[var(--pv-surface-2)]"
                @click="favorite(folder.id)"
              >
                {{ folder.name }}
              </button>
            </div>
          </div>
          <div v-if="store.settings.playlist_enabled !== false" class="relative">
            <button class="btn-ghost" :class="playlists.some((item) => item.contains) ? '!text-[var(--pv-accent)]' : ''" @click="showPlaylists = !showPlaylists">
              <Icon name="list" :size="16" />合集
            </button>
            <div v-if="showPlaylists" class="absolute left-0 top-full z-20 mt-1 w-56 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-1.5">
              <p v-if="!store.isLogin" class="px-3 py-2 text-xs muted">登录后可以加入合集</p>
              <template v-else>
                <button
                  v-for="item in playlists"
                  :key="item.id"
                  class="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm hover:bg-[var(--pv-surface-2)]"
                  @click="togglePlaylist(item)"
                >
                  <span class="truncate">{{ item.title }}</span>
                  <span v-if="item.contains" class="shrink-0 text-xs text-[var(--pv-accent)]">已加入</span>
                </button>
                <p v-if="!playlists.length" class="px-3 py-2 text-xs muted">还没有合集</p>
              </template>
              <RouterLink to="/playlists" class="mt-1 block rounded-xl px-3 py-2 text-xs text-[var(--pv-accent)] hover:bg-[var(--pv-surface-2)]" @click="showPlaylists = false">
                管理我的合集 →
              </RouterLink>
            </div>
          </div>
          <button class="btn-ghost" @click="share"><Icon name="share" :size="16" />分享</button>
          <button v-if="store.settings.charge_enabled !== false && !video.canEdit" class="btn-ghost" @click="showCharge = true">
            <Icon name="zap" :size="16" />充电
          </button>
          <button v-if="store.settings.allow_report !== false" class="btn-ghost" @click="showReport = true">
            <Icon name="flag" :size="16" />举报
          </button>
        </div>
      </div>

      <div class="surface p-4">
        <div class="flex flex-wrap items-start gap-3">
          <RouterLink :to="`/space/${video.author.username}`" class="shrink-0">
            <img v-if="video.author.avatar" :src="video.author.avatar" class="h-12 w-12 rounded-full object-cover" alt="" />
            <span v-else class="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] font-bold text-white">
              {{ initials(video.author.displayName) }}
            </span>
          </RouterLink>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <RouterLink :to="`/space/${video.author.username}`" class="font-medium hover:text-[var(--pv-accent)]">
                {{ video.author.displayName }}
              </RouterLink>
              <span class="chip !py-0 text-[10px]">Lv{{ video.author.level }}</span>
              <span class="text-xs muted">{{ formatNumber(video.author.followerCount) }} 粉丝</span>
            </div>
            <p class="mt-1 line-clamp-2 text-xs muted">{{ video.author.bio || '这个人很神秘，什么都没写' }}</p>
          </div>
          <div class="flex shrink-0 gap-2">
            <RouterLink v-if="store.isLogin && !video.canEdit" :to="`/messages?to=${video.author.username}`" class="btn-ghost text-xs">
              <Icon name="message" :size="15" />私信
            </RouterLink>
            <button v-if="!video.canEdit" class="btn-primary text-xs" @click="toggleFollow">
              {{ following ? '已关注' : '关注' }}
            </button>
            <RouterLink v-else to="/upload" class="btn-ghost text-xs">投稿管理</RouterLink>
          </div>
        </div>

        <div class="mt-3 whitespace-pre-wrap border-t border-[var(--pv-border)] pt-3 text-sm leading-relaxed">
          {{ video.description || '这个 UP 主很懒，什么都没写' }}
        </div>

        <div v-if="video.tags?.length || video.category" class="mt-3 flex flex-wrap gap-2">
          <RouterLink v-if="video.category" :to="`/category/${video.category.slug}`" class="chip !border-[var(--pv-accent)]/40 !text-[var(--pv-accent)]">
            {{ video.category.name }}
          </RouterLink>
          <RouterLink
            v-for="tag in video.tags"
            :key="tag.id"
            :to="`/search?q=${encodeURIComponent(tag.name)}`"
            class="chip hover:!text-[var(--pv-accent)]"
          >
            # {{ tag.name }}
          </RouterLink>
        </div>
      </div>

      <div class="surface p-4">
        <div class="mb-3 flex items-center gap-2">
          <button
            class="rounded-full px-3 py-1 text-sm"
            :class="panel === 'comments' ? 'bg-[var(--pv-surface-2)] font-medium' : 'muted'"
            @click="panel = 'comments'"
          >
            评论 {{ video.comments }}
          </button>
          <button
            v-if="notesOpen"
            class="rounded-full px-3 py-1 text-sm"
            :class="panel === 'notes' ? 'bg-[var(--pv-surface-2)] font-medium' : 'muted'"
            @click="panel = 'notes'"
          >
            笔记 {{ notes.length }}
          </button>
        </div>

        <div v-if="panel === 'notes'" class="space-y-3">
          <template v-if="store.isLogin">
            <div class="rounded-2xl border border-[var(--pv-border)] p-3">
              <textarea
                v-model="noteDraft"
                class="input min-h-[70px]"
                placeholder="在当前位置记一条笔记，点下方时间可以跳回去看"
              />
              <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
                <label class="flex items-center gap-2 text-xs muted">
                  <input v-model="notePublic" type="checkbox" />公开这条笔记
                </label>
                <div class="flex items-center gap-2">
                  <span class="text-xs muted">记录位置 {{ clock(player?.position?.() || 0) }}</span>
                  <button class="btn-primary text-xs" :disabled="!noteDraft.trim()" @click="saveNote">保存笔记</button>
                </div>
              </div>
            </div>
          </template>
          <p v-else class="text-xs muted">登录后可以在这里记笔记。</p>

          <div v-if="notes.length" class="space-y-2">
            <div v-for="item in notes" :key="item.id" class="rounded-2xl bg-[var(--pv-surface-2)] p-3">
              <div class="flex items-center gap-2">
                <button class="chip !py-0 text-[11px] hover:!text-[var(--pv-accent)]" @click="jumpTo(item.time)">
                  {{ clock(item.time) }}
                </button>
                <span class="text-xs muted">{{ item.author?.displayName }}</span>
                <span v-if="!item.isPublic" class="chip !py-0 text-[10px]">仅自己可见</span>
                <span class="ml-auto text-[11px] muted">{{ fromNow(item.createdAt) }}</span>
              </div>
              <p class="mt-1.5 whitespace-pre-wrap text-sm">{{ item.content }}</p>
              <div v-if="item.isMine" class="mt-1.5 flex gap-3 text-[11px]">
                <button class="muted hover:text-[var(--pv-accent)]" @click="toggleNotePublic(item)">
                  {{ item.isPublic ? '设为私密' : '设为公开' }}
                </button>
                <button class="text-rose-500 hover:underline" @click="removeNote(item)">删除</button>
              </div>
            </div>
          </div>
          <p v-else class="text-xs muted">还没有笔记，边看边记一条吧。</p>
        </div>

        <CommentList v-else :video-id="video.id" :allow-comment="Boolean(video.allowComment)" />
      </div>
    </div>

    <aside class="space-y-3">
      <h3 class="text-sm font-semibold">相关推荐</h3>
      <RouterLink
        v-for="item in related"
        :key="item.id"
        :to="`/video/${item.id}`"
        class="flex gap-2 rounded-2xl p-1.5 transition hover:bg-[var(--pv-surface-2)]"
      >
        <img :src="item.cover" class="h-14 w-24 shrink-0 rounded-xl object-cover" alt="" />
        <div class="min-w-0">
          <p class="line-clamp-2 text-xs font-medium">{{ item.title }}</p>
          <p class="mt-1 text-[11px] muted">{{ item.author.displayName }} · {{ formatNumber(item.views) }} 播放</p>
        </div>
      </RouterLink>
      <p v-if="!related.length" class="text-xs muted">暂无相关推荐</p>
    </aside>

    <div v-if="showReport" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="showReport = false">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h3 class="text-sm font-semibold">举报视频</h3>
        <select v-model="reportReason" class="input">
          <option v-for="item in reasons" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <textarea v-model="reportDetail" class="input min-h-[80px]" placeholder="补充说明（可选）"></textarea>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="showReport = false">取消</button>
          <button class="btn-primary" @click="report">提交举报</button>
        </div>
      </div>
    </div>

    <div v-if="showCharge" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="showCharge = false">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold"><Icon name="zap" :size="16" />给 {{ video.author.displayName }} 充电</h3>
        <p class="text-xs muted">
          用硬币支持创作者，当前比例 {{ store.settings.charge_ratio ?? 100 }} 硬币 = 1 元，
          创作者分成 {{ store.settings.creator_share_percent ?? 70 }}%。
          我的硬币：{{ store.user?.coins ?? 0 }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button v-for="value in [10, 50, 100, 500]" :key="value" class="chip !px-3 !py-1.5" :class="chargeCoins === value ? '!border-[var(--pv-accent)] !text-[var(--pv-accent)]' : ''" @click="chargeCoins = value">
            {{ value }} 硬币
          </button>
        </div>
        <input v-model.number="chargeCoins" type="number" min="1" class="input" />
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="showCharge = false">取消</button>
          <button class="btn-primary" @click="charge">确认充电</button>
        </div>
      </div>
    </div>
  </div>
</template>
