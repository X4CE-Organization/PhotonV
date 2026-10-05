<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { api, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatNumber, fromNow, initials } from '../utils';
import VideoCard from '../components/VideoCard.vue';
import PaginationBar from '../components/PaginationBar.vue';
import Icon from '../components/Icon.vue';

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
const showCharge = ref(false);
const chargeCoins = ref(50);

async function charge() {
  try {
    await api.post('/api/orders', {
      type: 'charge',
      username: String(route.params.username),
      coins: Number(chargeCoins.value) || 0,
    });
    showCharge.value = false;
    toast.success('充电成功，感谢支持创作者');
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '充电失败');
  }
}

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

const playlists = ref<any[]>([]);
const moments = ref<any[]>([]);
const momentTotal = ref(0);
const momentPage = ref(1);
const momentContent = ref('');
const momentImages = ref<string[]>([]);
const momentPrivate = ref(false);
const momentPosting = ref(false);
const momentUploading = ref(false);

async function loadMoments() {
  try {
    const result = await api.get<any>(
      `/api/users/${route.params.username}/moments${query({ page: momentPage.value, size: 10 })}`,
    );
    moments.value = result.items || [];
    momentTotal.value = result.total || 0;
  } catch {
    moments.value = [];
    momentTotal.value = 0;
  }
}

async function uploadMomentImage(files: FileList | null) {
  if (!files?.length) return;
  momentUploading.value = true;
  try {
    for (const file of Array.from(files).slice(0, 9 - momentImages.value.length)) {
      const result = await api.upload<{ url: string }>('/api/upload/image', file);
      momentImages.value.push(result.url);
    }
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '图片上传失败');
  } finally {
    momentUploading.value = false;
  }
}

async function publishMoment() {
  if (!momentContent.value.trim() && !momentImages.value.length) {
    toast.info('写点什么或者配张图吧');
    return;
  }
  momentPosting.value = true;
  try {
    await api.post('/api/moments', {
      content: momentContent.value.trim(),
      images: momentImages.value,
      is_private: momentPrivate.value,
    });
    momentContent.value = '';
    momentImages.value = [];
    momentPrivate.value = false;
    momentPage.value = 1;
    toast.success('已发布');
    await loadMoments();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '发布失败');
  } finally {
    momentPosting.value = false;
  }
}

async function likeMoment(item: any) {
  if (!store.isLogin) return toast.info('请先登录');
  try {
    const result = await api.post<any>(`/api/moments/${item.id}/like`);
    item.liked = result.liked;
    item.likeCount = result.likeCount;
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

async function deleteMoment(item: any) {
  try {
    await api.del(`/api/moments/${item.id}`);
    toast.success('已删除');
    await loadMoments();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  }
}

async function loadPlaylists() {
  try {
    const result = await api.get<any>(`/api/users/${route.params.username}/playlists`);
    playlists.value = result.items || [];
  } catch {
    playlists.value = [];
  }
}

function switchTab(value: string) {
  tab.value = value;
  if (value === 'followers') void loadFollows('followers');
  else if (value === 'following') void loadFollows('following');
  else if (value === 'playlists') void loadPlaylists();
  else if (value === 'moments') void loadMoments();
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
  momentPage.value = 1;
  tab.value = 'videos';
  void load();
});
onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <div v-else-if="data" class="space-y-4">
    <div class="surface overflow-hidden">
      <div
        class="h-32 bg-gradient-to-r from-primary/60 to-indigo-500/60"
        :style="data.banner ? { backgroundImage: `url(${data.banner})`, backgroundSize: 'cover', backgroundPosition: 'center' } : {}"
      ></div>
      <div class="flex flex-wrap items-end gap-4 px-4 pb-4">
        <img
          v-if="data.avatar"
          :src="data.avatar"
          class="-mt-10 h-20 w-20 rounded-full border-4 border-white object-cover"
          alt=""
        />
        <span
          v-else
          class="-mt-10 grid h-20 w-20 place-items-center rounded-full border-4 border-white bg-[var(--pv-accent)]/15 text-2xl font-semibold text-[var(--pv-accent)]"
        >
          {{ initials(data.displayName) }}
        </span>
        <div class="flex-1">
          <h1 class="text-lg font-semibold">{{ data.displayName }}</h1>
          <p class="text-xs muted">@{{ data.username }} · 加入于 {{ fromNow(data.joinedAt) }}</p>
          <p class="mt-1 text-sm muted">{{ data.bio || '这个人很神秘，什么都没写' }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <RouterLink v-if="isSelf()" to="/settings" class="btn-ghost text-xs">编辑资料</RouterLink>
          <template v-else>
            <RouterLink v-if="store.isLogin" :to="`/messages?to=${encodeURIComponent(String(route.params.username))}`" class="btn-ghost text-xs">
              <Icon name="message" :size="15" />私信
            </RouterLink>
            <button v-if="store.isLogin && store.settings.charge_enabled !== false" class="btn-ghost text-xs" @click="showCharge = true">
              <Icon name="zap" :size="15" />充电
            </button>
            <button class="btn-primary text-xs" @click="toggleFollow">{{ following ? '已关注' : '关注' }}</button>
          </template>
        </div>
      </div>
      <div class="flex flex-wrap gap-6 border-t border border-[var(--pv-border)] px-4 py-3 text-sm">
        <button class="hover:text-[var(--pv-accent)]" @click="switchTab('videos')"><b>{{ data.videoCount }}</b> <span class="text-xs muted">投稿</span></button>
        <button class="hover:text-[var(--pv-accent)]" @click="switchTab('followers')"><b>{{ data.followers }}</b> <span class="text-xs muted">粉丝</span></button>
        <button class="hover:text-[var(--pv-accent)]" @click="switchTab('following')"><b>{{ data.following }}</b> <span class="text-xs muted">关注</span></button>
        <button
          class="inline-flex items-center gap-1 hover:text-[var(--pv-accent)]"
          @click="switchTab('playlists')"
        >
          <Icon name="list" :size="14" /><span class="text-xs muted">合集</span>
        </button>
        <button
          v-if="store.settings.moments_enabled !== false"
          class="inline-flex items-center gap-1 hover:text-[var(--pv-accent)]"
          :class="tab === 'moments' ? 'text-[var(--pv-accent)]' : ''"
          @click="switchTab('moments')"
        >
          <Icon name="message" :size="14" /><span class="text-xs muted">动态</span>
        </button>
        <span><b>{{ formatNumber(data.playCount) }}</b> <span class="text-xs muted">总播放</span></span>
        <span><b>{{ formatNumber(data.likeCount) }}</b> <span class="text-xs muted">获赞</span></span>
        <span v-if="level" class="ml-auto text-xs muted">
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
          :class="status === item.key ? 'bg-[var(--pv-accent)]/10 font-medium text-[var(--pv-accent)]' : 'muted'"
          @click="status = item.key; page = 1; load()"
        >
          {{ item.label }}
        </button>
      </div>

      <p v-if="!items.length" class="surface p-16 text-center text-sm muted">还没有投稿</p>
      <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <VideoCard v-for="video in items" :key="video.id" :video="video" />
      </div>
      <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />
    </template>

    <template v-else-if="tab === 'moments'">
      <div v-if="isSelf()" class="surface space-y-3 p-4">
        <textarea
          v-model="momentContent"
          class="input min-h-[88px] resize-y"
          :maxlength="Number(store.settings.moment_max_length ?? 2000)"
          placeholder="记录点什么…（动态只出现在个人主页）"
        ></textarea>
        <div v-if="momentImages.length" class="flex flex-wrap gap-2">
          <div v-for="(img, index) in momentImages" :key="img" class="relative h-20 w-20 overflow-hidden rounded-lg border border-[var(--pv-border)]">
            <img :src="img" class="h-full w-full object-cover" alt="" />
            <button
              class="absolute right-1 top-1 grid h-5 w-5 place-items-center rounded bg-black/60 text-xs text-white"
              @click="momentImages.splice(index, 1)"
            >
              ×
            </button>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <label class="btn-ghost cursor-pointer text-xs">
            {{ momentUploading ? '上传中…' : '添加图片' }}
            <input type="file" accept="image/*" multiple class="hidden" @change="(e) => uploadMomentImage((e.target as HTMLInputElement).files)" />
          </label>
          <label class="flex items-center gap-1.5 text-xs muted">
            <input v-model="momentPrivate" type="checkbox" />
            仅自己可见
          </label>
          <button class="btn-primary ml-auto text-xs" :disabled="momentPosting" @click="publishMoment">发布</button>
        </div>
      </div>

      <p v-if="!moments.length" class="surface p-16 text-center text-sm muted">还没有动态</p>
      <div v-else class="space-y-3">
        <article v-for="item in moments" :key="item.id" class="surface space-y-3 p-4">
          <div class="flex items-center gap-2 text-xs muted">
            <span>{{ fromNow(item.createdAt) }}</span>
            <span v-if="item.isPrivate" class="chip !px-2 !py-0.5">仅自己可见</span>
            <button v-if="item.isMine" class="ml-auto hover:text-[var(--pv-danger)]" @click="deleteMoment(item)">删除</button>
          </div>
          <p v-if="item.content" class="whitespace-pre-wrap break-words text-sm">{{ item.content }}</p>
          <div v-if="item.images?.length" class="grid grid-cols-3 gap-2 sm:grid-cols-4">
            <a v-for="img in item.images" :key="img" :href="img" target="_blank" rel="noreferrer" class="overflow-hidden rounded-lg border border-[var(--pv-border)]">
              <img :src="img" class="aspect-square w-full object-cover" alt="" />
            </a>
          </div>
          <div class="flex items-center gap-4 border-t border-[var(--pv-border)] pt-2 text-xs">
            <button class="inline-flex items-center gap-1" :class="item.liked ? 'text-[var(--pv-accent)]' : 'muted'" @click="likeMoment(item)">
              <Icon name="heart" :size="14" />{{ item.likeCount }}
            </button>
          </div>
        </article>
      </div>
      <div v-if="momentTotal > 10" class="flex justify-center gap-2">
        <button class="btn-ghost text-xs" :disabled="momentPage <= 1" @click="momentPage -= 1; loadMoments()">上一页</button>
        <span class="self-center text-xs muted">{{ momentPage }}</span>
        <button class="btn-ghost text-xs" :disabled="momentPage * 10 >= momentTotal" @click="momentPage += 1; loadMoments()">下一页</button>
      </div>
    </template>

    <template v-else-if="tab === 'playlists'">
      <p v-if="!playlists.length" class="surface p-16 text-center text-sm muted">还没有公开的合集</p>
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <RouterLink
          v-for="item in playlists"
          :key="item.id"
          :to="`/playlist/${item.id}`"
          class="surface overflow-hidden hover:shadow-md"
        >
          <img v-if="item.cover" :src="item.cover" class="h-28 w-full object-cover" alt="" />
          <div v-else class="grid h-28 w-full place-items-center bg-[var(--pv-accent)]/5 text-xs muted">暂无封面</div>
          <div class="space-y-1 p-3">
            <div class="line-clamp-1 text-sm font-medium">{{ item.title }}</div>
            <p class="line-clamp-2 text-xs muted">{{ item.description || '暂无简介' }}</p>
            <p class="text-[11px] muted">{{ item.videoCount }} 个视频</p>
          </div>
        </RouterLink>
      </div>
    </template>

    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <RouterLink
        v-for="user in follows"
        :key="user.id"
        :to="`/space/${user.username}`"
        class="surface flex items-center gap-3 p-3 hover:shadow-md"
      >
        <img v-if="user.avatar" :src="user.avatar" class="h-11 w-11 rounded-full object-cover" alt="" />
        <span v-else class="grid h-11 w-11 place-items-center rounded-full bg-[var(--pv-accent)]/15 font-semibold text-[var(--pv-accent)]">
          {{ initials(user.displayName) }}
        </span>
        <div class="min-w-0">
          <div class="text-sm font-medium">{{ user.displayName }}</div>
          <p class="text-xs muted">{{ formatNumber(user.followerCount) }} 粉丝</p>
        </div>
      </RouterLink>
      <p v-if="!follows.length" class="col-span-full py-10 text-center text-sm muted">暂无数据</p>
    </div>

    <div v-if="showCharge" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="showCharge = false">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold"><Icon name="zap" :size="16" />给 {{ data.displayName }} 充电</h3>
        <p class="text-xs muted">
          {{ store.settings.charge_ratio ?? 100 }} 硬币 = 1 元，创作者分成 {{ store.settings.creator_share_percent ?? 70 }}%。
          我的硬币：{{ store.user?.coins ?? 0 }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="value in [10, 50, 100, 500]"
            :key="value"
            class="chip !px-3 !py-1.5"
            :class="chargeCoins === value ? '!border-[var(--pv-accent)] !text-[var(--pv-accent)]' : ''"
            @click="chargeCoins = value"
          >
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
