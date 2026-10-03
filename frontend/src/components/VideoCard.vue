<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { formatDuration, formatNumber, initials } from '../utils';

defineProps<{ video: any; compact?: boolean }>();
</script>

<template>
  <RouterLink
    :to="`/video/${video.id}`"
    class="group block overflow-hidden rounded-xl border border-slate-200 bg-white transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
  >
    <div class="relative aspect-video overflow-hidden bg-slate-100 dark:bg-slate-800">
      <img v-if="video.cover" :src="video.cover" :alt="video.title" class="h-full w-full object-cover transition group-hover:scale-[1.03]" />
      <div v-else class="grid h-full w-full place-items-center text-slate-400">无封面</div>
      <span class="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
        {{ formatDuration(video.duration) }}
      </span>
      <span
        v-if="video.status && video.status !== 'published'"
        class="absolute left-1 top-1 rounded bg-amber-500/90 px-1.5 py-0.5 text-[11px] text-white"
      >
        {{ video.status === 'pending' ? '审核中' : video.status === 'rejected' ? '未通过' : '仅自己可见' }}
      </span>
      <span v-if="video.isPinned" class="absolute right-1 top-1 rounded bg-primary/90 px-1.5 py-0.5 text-[11px] text-white">置顶</span>
    </div>
    <div class="p-2.5">
      <h3 class="line-clamp-2 text-sm font-medium leading-snug">{{ video.title }}</h3>
      <div class="mt-2 flex items-center gap-2 text-xs text-slate-400">
        <img v-if="video.author?.avatar" :src="video.author.avatar" class="h-5 w-5 rounded-full object-cover" alt="" />
        <span v-else class="grid h-5 w-5 place-items-center rounded-full bg-primary/15 text-[10px] text-primary">
          {{ initials(video.author?.displayName) }}
        </span>
        <span class="truncate">{{ video.author?.displayName }}</span>
      </div>
      <div class="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-400">
        <span>▶ {{ formatNumber(video.views) }}</span>
        <span>💬 {{ formatNumber(video.comments) }}</span>
        <span>👍 {{ formatNumber(video.likes) }}</span>
      </div>
    </div>
  </RouterLink>
</template>
