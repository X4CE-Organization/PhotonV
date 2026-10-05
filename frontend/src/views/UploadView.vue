<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { api, getToken, query } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatDuration, formatSize, fromNow } from '../utils';
import VideoCard from '../components/VideoCard.vue';
import PageHead from '../components/PageHead.vue';

const store = useAppStore();
const router = useRouter();
const fileInput = ref<HTMLInputElement | null>(null);
const videoEl = ref<HTMLVideoElement | null>(null);
const uploadPercent = ref(0);
const uploading = ref(false);
const submitting = ref(false);
const form = ref({
  title: '',
  description: '',
  category_id: '' as number | '',
  tags: '',
  source: '',
  source_url: '',
  cover: '',
  duration: 0,
  filesize: 0,
  allow_comment: true,
  allow_danmaku: true,
  allow_download: true,
  scheduled_at: '',
});
const myVideos = ref<any[]>([]);
const statusFilter = ref('all');

const canSubmit = computed(() => form.value.title.trim().length >= 2 && Boolean(form.value.source || form.value.source_url));

function uploadVideoFile(file: File) {
  uploading.value = true;
  uploadPercent.value = 0;
  const data = new FormData();
  data.append('file', file);
  const request = new XMLHttpRequest();
  request.open('POST', '/api/upload/video');
  const token = getToken();
  if (token) request.setRequestHeader('Authorization', `Bearer ${token}`);
  request.upload.onprogress = (event) => {
    if (event.lengthComputable) uploadPercent.value = Math.round((event.loaded / event.total) * 100);
  };
  request.onload = () => {
    uploading.value = false;
    if (request.status >= 200 && request.status < 300) {
      const result = JSON.parse(request.responseText);
      form.value.source = result.url;
      form.value.filesize = result.size;
      toast.success('视频上传完成');
      void probeVideo(result.url);
    } else {
      try {
        toast.error(JSON.parse(request.responseText).message || '上传失败');
      } catch {
        toast.error('上传失败');
      }
    }
  };
  request.onerror = () => {
    uploading.value = false;
    toast.error('上传失败，请检查网络');
  };
  request.send(data);
}

/** 用浏览器读取时长并截取一帧作为封面，省去服务端转码依赖 */
async function probeVideo(url: string) {
  const element = videoEl.value;
  if (!element) return;
  element.src = url;
  await new Promise<void>((resolve) => {
    element.onloadedmetadata = () => resolve();
    element.onerror = () => resolve();
  });
  form.value.duration = Math.round(element.duration || 0);
  try {
    element.currentTime = Math.min(1, (element.duration || 2) / 3);
    await new Promise<void>((resolve) => {
      element.onseeked = () => resolve();
      setTimeout(resolve, 1500);
    });
    const canvas = document.createElement('canvas');
    canvas.width = element.videoWidth || 640;
    canvas.height = element.videoHeight || 360;
    canvas.getContext('2d')?.drawImage(element, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
    if (!blob) return;
    const file = new File([blob], 'cover.jpg', { type: 'image/jpeg' });
    const result = await api.upload<{ url: string }>('/api/upload/image', file);
    form.value.cover = result.url;
    toast.success('已自动生成封面，可手动替换');
  } catch {
    /* 封面失败不影响投稿 */
  }
}

async function pickCover(file: File) {
  const result = await api.upload<{ url: string }>('/api/upload/image', file);
  form.value.cover = result.url;
  toast.success('封面已上传');
}

async function submit() {
  if (!canSubmit.value) {
    toast.error('请填写标题并上传视频');
    return;
  }
  submitting.value = true;
  try {
    const result = await api.post<any>('/api/videos', {
      ...form.value,
      category_id: form.value.category_id || null,
      tags: form.value.tags
        .split(/[,，\s]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    });
    toast.success(result.status === 'pending' ? '投稿成功，等待管理员审核' : '发布成功');
    void loadMine();
    router.push(`/video/${result.id}`);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '投稿失败');
  } finally {
    submitting.value = false;
  }
}

async function loadMine() {
  if (!store.user) return;
  const data = await api.get<any>(
    `/api/users/${store.user.username}/videos${query({ status: statusFilter.value, size: 24 })}`,
  );
  myVideos.value = data.items || [];
}

async function setStatus(video: any, status: string) {
  try {
    await api.post(`/api/videos/${video.id}/visibility`, { status });
    toast.success('已更新');
    void loadMine();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

async function removeVideo(video: any) {
  if (!window.confirm(`确定删除《${video.title}》吗？`)) return;
  await api.del(`/api/videos/${video.id}`);
  toast.success('已删除');
  void loadMine();
}

onMounted(loadMine);
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">
    <div class="space-y-4">
      <PageHead icon="upload" title="投稿" :subtitle="String(store.settings.video_review_note || '')" />
      <div class="surface p-4">

        <div class="mt-4 space-y-3">
          <div>
            <label class="label">视频文件</label>
            <input
              ref="fileInput"
              type="file"
              accept="video/*"
              class="hidden"
              @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) uploadVideoFile(file); }"
            />
            <div class="flex flex-wrap items-center gap-2">
              <button class="btn-ghost" :disabled="uploading" @click="fileInput?.click()">
                {{ uploading ? '上传中…' : '选择视频文件' }}
              </button>
              <span v-if="form.source" class="text-xs text-emerald-600">{{ form.source }} · {{ formatSize(form.filesize) }}</span>
              <span v-if="uploading" class="text-xs muted">{{ uploadPercent }}%</span>
            </div>
            <div v-if="uploading" class="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--pv-surface-2)]">
              <div class="h-full bg-[var(--pv-accent)] transition-all" :style="{ width: uploadPercent + '%' }"></div>
            </div>
          </div>

          <div v-if="store.settings.allow_video_url !== false">
            <label class="label">或填写外部视频直链</label>
            <input v-model="form.source_url" class="input" placeholder="https://example.com/video.mp4" />
          </div>

          <div>
            <label class="label">标题</label>
            <input v-model="form.title" class="input" maxlength="80" placeholder="起个吸引人的标题吧" />
          </div>

          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label class="label">分区</label>
              <select v-model="form.category_id" class="input">
                <option value="">未选择</option>
                <option v-for="item in store.categories" :key="item.id" :value="item.id">{{ item.icon }} {{ item.name }}</option>
              </select>
            </div>
            <div>
              <label class="label">标签（逗号分隔）</label>
              <input v-model="form.tags" class="input" placeholder="开源, 教程" />
            </div>
          </div>

          <div>
            <label class="label">简介</label>
            <textarea v-model="form.description" class="input min-h-[120px]" placeholder="介绍一下这个视频的内容"></textarea>
          </div>

          <div>
            <label class="label">封面</label>
            <div class="flex items-center gap-3">
              <img v-if="form.cover" :src="form.cover" class="h-16 w-28 rounded object-cover" alt="cover" />
              <label class="btn-ghost cursor-pointer">
                上传封面
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) pickCover(file); }"
                />
              </label>
              <span class="text-xs muted">不传会自动截取视频画面</span>
            </div>
          </div>

          <div class="flex flex-wrap gap-4 text-sm muted">
            <label class="flex items-center gap-2"><input v-model="form.allow_comment" type="checkbox" />允许评论</label>
            <label class="flex items-center gap-2"><input v-model="form.allow_danmaku" type="checkbox" />允许弹幕</label>
            <label class="flex items-center gap-2"><input v-model="form.allow_download" type="checkbox" />允许下载</label>
          </div>

          <div v-if="store.settings.scheduled_publish_enabled !== false">
            <label class="label">定时发布（可选）</label>
            <input v-model="form.scheduled_at" type="datetime-local" class="input sm:max-w-xs" />
            <p class="mt-1 text-xs muted">
              留空就按正常流程发布。填了时间的话，到点会自动公开，最多支持 30 天内。
            </p>
          </div>

          <div class="flex justify-end">
            <button class="btn-primary" :disabled="submitting || !canSubmit" @click="submit">
              {{ submitting ? '提交中…' : '发布投稿' }}
            </button>
          </div>
        </div>
        <video ref="videoEl" class="hidden"></video>
      </div>
    </div>

    <aside class="surface p-4">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold">我的投稿</h2>
        <select v-model="statusFilter" class="input !w-28 !py-1 text-xs" @change="loadMine">
          <option value="all">全部</option>
          <option value="published">已公开</option>
          <option value="pending">审核中</option>
          <option value="rejected">未通过</option>
          <option value="private">仅自己</option>
        </select>
      </div>
      <ul class="mt-3 space-y-3">
        <li v-for="video in myVideos" :key="video.id" class="rounded-lg border border-[var(--pv-border)] p-2">
          <div class="flex gap-2">
            <img :src="video.cover" class="h-12 w-20 shrink-0 rounded object-cover" alt="" />
            <div class="min-w-0 flex-1">
              <RouterLink :to="`/video/${video.id}`" class="line-clamp-2 text-xs font-medium hover:text-[var(--pv-accent)]">{{ video.title }}</RouterLink>
              <p class="mt-0.5 text-[11px] muted">
                {{ video.status === 'published' ? '已公开' : video.status === 'pending' ? '审核中' : video.status === 'rejected' ? '未通过' : '仅自己' }}
                · {{ formatDuration(video.duration) }} · {{ fromNow(video.createdAt) }}
              </p>
            </div>
          </div>
          <div class="mt-1.5 flex gap-2 text-[11px]">
            <button v-if="video.status !== 'published'" class="text-[var(--pv-accent)]" @click="setStatus(video, 'published')">设为公开</button>
            <button v-if="video.status !== 'private'" class="muted" @click="setStatus(video, 'private')">设为私密</button>
            <button class="text-rose-500" @click="removeVideo(video)">删除</button>
          </div>
        </li>
        <li v-if="!myVideos.length" class="py-6 text-center text-xs muted">还没有投稿</li>
      </ul>
    </aside>
  </div>
</template>
