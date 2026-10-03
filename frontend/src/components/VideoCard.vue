<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { formatDuration, formatNumber, initials } from '../utils';
import Icon from './Icon.vue';

defineProps<{ video: any; compact?: boolean }>();
</script>

<template>
  <RouterLink
    :to="`/video/${video.id}`"
    class="group block overflow-hidden rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] transition hover:-translate-y-0.5 hover:border-[var(--pv-accent)]/50"
  >
    <div class="relative aspect-video overflow-hidden bg-[var(--pv-surface-2)]">
      <img
        v-if="video.cover"
        :src="video.cover"
        :alt="video.title"
        class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
      />
      <div v-else class="grid h-full w-full place-items-center text-xs muted">暂无封面</div>

      <div class="absolute inset-0 flex items-center justify-center bg-black/25 opacity-0 transition group-hover:opacity-100">
        <span class="grid h-12 w-12 place-items-center rounded-full bg-white/90 text-[#6d4aff]">
          <Icon name="play" :size="22" />
        </span>
      </div>

      <span class="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[11px] font-medium text-white">
        {{ formatDuration(video.duration) }}
      </span>
      <span
        v-if="video.status && video.status !== 'published'"
        class="absolute left-2 top-2 rounded-md bg-amber-500/90 px-1.5 py-0.5 text-[11px] font-medium text-white"
      >
        {{ video.status === 'pending' ? '审核中' : video.status === 'rejected' ? '未通过' : '仅自己可见' }}
      </span>
      <span v-if="video.isPinned" class="absolute right-2 top-2 rounded-md bg-[#6d4aff]/90 px-1.5 py-0.5 text-[11px] font-medium text-white">
        置顶
      </span>
    </div>

    <div class="space-y-2 p-3">
      <h3 class="line-clamp-2 text-[13.5px] font-medium leading-snug">{{ video.title }}</h3>
      <div class="flex items-center gap-2 text-xs muted">
        <img v-if="video.author?.avatar" :src="video.author.avatar" class="h-5 w-5 rounded-full object-cover" alt="" />
        <span
          v-else
          class="grid h-5 w-5 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-[10px] font-bold text-white"
        >
          {{ initials(video.author?.displayName) }}
        </span>
        <span class="truncate">{{ video.author?.displayName }}</span>
      </div>
      <div class="flex items-center gap-3 text-[11px] muted">
        <span class="inline-flex items-center gap-1"><Icon name="play" :size="12" />{{ formatNumber(video.views) }}</span>
        <span class="inline-flex items-center gap-1"><Icon name="message" :size="12" />{{ formatNumber(video.comments) }}</span>
        <span class="inline-flex items-center gap-1"><Icon name="heart" :size="12" />{{ formatNumber(video.likes) }}</span>
      </div>
    </div>
  </RouterLink>
</template>
