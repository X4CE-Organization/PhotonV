<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{ name: string; size?: number | string; stroke?: number }>(), {
  size: 20,
  stroke: 1.8,
});

/**
 * 全站统一的 SVG 图标集（不使用 emoji）。
 * 用法：<Icon name="home" :size="18" />
 */
const ICONS: Record<string, string> = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V20a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V9.5"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.6 8.4-2.1 5.1-5.1 2.1 2.1-5.1z"/>',
  flame: '<path d="M12 3c3 3.6 6 6.2 6 10a6 6 0 0 1-12 0c0-2.1 1-3.6 2.6-5.2"/>',
  upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
  radio: '<circle cx="12" cy="12" r="2.6"/><path d="M5.6 5.6a9 9 0 0 0 0 12.8"/><path d="M18.4 5.6a9 9 0 0 1 0 12.8"/>',
  send: '<path d="m4 12 16-8-6 16-3-7z"/>',
  bell: '<path d="M6.5 9.5a5.5 5.5 0 1 1 11 0c0 4.6 1.8 5.8 1.8 5.8H4.7s1.8-1.2 1.8-5.8z"/><path d="M10 19a2 2 0 0 0 4 0"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.4 2.9-5.5 6.5-5.5s6.5 2.1 6.5 5.5"/><path d="M16 4.8a3.4 3.4 0 0 1 0 6.8"/><path d="M18 14.8c2 .7 3.5 2.2 3.5 4.4"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.4M12 18.6V21M3 12h2.4M18.6 12H21M5.6 5.6l1.7 1.7M16.7 16.7l1.7 1.7M18.4 5.6l-1.7 1.7M7.3 16.7l-1.7 1.7"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
  play: '<path d="M8.5 5.6v12.8L19 12z"/>',
  heart: '<path d="M12 20s-7-4.4-7-9.4A3.9 3.9 0 0 1 12 7.2 3.9 3.9 0 0 1 19 10.6c0 5-7 9.4-7 9.4z"/>',
  coin: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.8v8.4M9.6 9.9h4.8M9.6 14.1h4.8"/>',
  star: '<path d="m12 4 2.4 5 5.6.8-4 4 .9 5.6L12 17l-4.9 2.4.9-5.6-4-4L9.6 9z"/>',
  share: '<path d="M15 8.5V6l6 5-6 5v-2.5C11 13.5 8 15 6 18c0-5 3-8.5 9-9.5z"/>',
  flag: '<path d="M6 21V4c5-2 8 2 12 0v10c-4 2-7-2-12 0"/>',
  download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/>',
  expand: '<path d="M4 9V4h5M20 15v5h-5M15 4h5v5M9 20H4v-5"/>',
  'chevron-down': '<path d="m6 9.5 6 6 6-6"/>',
  'chevron-left': '<path d="m14 6-6 6 6 6"/>',
  'chevron-right': '<path d="m10 6 6 6-6 6"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  dashboard: '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M8 4v16M16 4v16"/>',
  shield: '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>',
  database: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
  key: '<circle cx="8" cy="15" r="3.5"/><path d="m10.6 12.4 8-8 2 2-2 2 1.5 1.5-2 2-1.5-1.5"/>',
  crown: '<path d="M4 17.5 3 7l5 3 4-6 4 6 5-3-1 10.5z"/><path d="M4 20.5h16"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4.5 7.5 7.5 5.5 7.5-5.5"/>',
  server: '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1.2"/><circle cx="4" cy="12" r="1.2"/><circle cx="4" cy="18" r="1.2"/>',
  trash: '<path d="M4 7h16M9.5 7V4.8h5V7M6.5 7l1 13h9l1-13"/>',
  edit: '<path d="M4 20h4L18.5 9.5l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  check: '<path d="m5 13 4.5 4.5L19 7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  logout: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="m10 8-4 4 4 4M6 12h9"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5 5l1.6 1.6M17.4 17.4 19 19M19 5l-1.6 1.6M6.6 17.4 5 19"/>',
  moon: '<path d="M20 14.6A8.6 8.6 0 0 1 9.4 4 8.5 8.5 0 1 0 20 14.6z"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3.4 2"/>',
  history: '<path d="M4 12a8 8 0 1 0 2.9-6.2"/><path d="M4 4v4h4"/><path d="M12 8v4.5l3 1.8"/>',
  bookmark: '<path d="M6.5 3.5h11v17l-5.5-4.2-5.5 4.2z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  video: '<rect x="3" y="6" width="12" height="12" rx="3"/><path d="m15.5 12 5.5-3.2v6.4z"/>',
  message: '<path d="M4 5.5h16v11H9.5L4 20.5z"/>',
  tv: '<rect x="2.5" y="6.5" width="19" height="12" rx="3"/><path d="m8 3.5 4 3 4-3"/>',
  card: '<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M2.5 10h19"/>',
  zap: '<path d="M13 3 5 14h5l-1 7 8-11h-5z"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4v4h-4"/>',
  eye: '<path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z"/><circle cx="12" cy="12" r="2.6"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 10.5V16M12 8h.01"/>',
  warning: '<path d="M12 4 3 19.5h18z"/><path d="M12 10v4M12 16.6h.01"/>',
  tag: '<path d="M4 4h8l8 8-8 8-8-8z"/><circle cx="8.5" cy="8.5" r="1.3"/>',
  folder: '<path d="M3 6.5a2 2 0 0 1 2-2h3.6l2 2.5H19a2 2 0 0 1 2 2v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  sparkles: '<path d="m12 3.5 1.7 4.3 4.3 1.7-4.3 1.7L12 15.5l-1.7-4.3L6 9.5l4.3-1.7z"/><path d="m18 15.5.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>',
  gamepad: '<rect x="2.5" y="8" width="19" height="9" rx="4.5"/><path d="M7 11v3M5.5 12.5h3M15.5 12h.01M17.5 14h.01"/>',
  book: '<path d="M4 5.5a2 2 0 0 1 2-2h13v17H6a2 2 0 0 1-2-2z"/><path d="M7 3.5v17"/>',
  cpu: '<rect x="7" y="7" width="10" height="10" rx="2.5"/><path d="M10 3v2M14 3v2M10 19v2M14 19v2M3 10h2M3 14h2M19 10h2M19 14h2"/>',
  music: '<path d="M9 18V6l10-2v12"/><circle cx="7" cy="18" r="2.4"/><circle cx="17" cy="16" r="2.4"/>',
  utensils: '<path d="M7 3v8a2 2 0 0 0 4 0V3"/><path d="M9 11v10"/><path d="M16 3c2 2 2 5 0 7v11"/>',
  dumbbell: '<path d="M4 9v6M7 6.5v11M17 6.5v11M20 9v6M7 12h10"/>',
  activity: '<path d="M3 12h4l2.5-6 4 12L16 12h5"/>',
  rocket: '<path d="M12 3c4 2 6 6 6 10l-6 5-6-5c0-4 2-8 6-10z"/><circle cx="12" cy="10" r="2"/>',
  dot: '<circle cx="12" cy="12" r="4"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
  palette:
    '<path d="M12 21a9 9 0 1 1 9-9c0 2.2-1.8 3.2-3.6 3.2H16a2 2 0 0 0-1.5 3.3A2 2 0 0 1 12 21z"/><circle cx="7.6" cy="12.4" r="1"/><circle cx="9.8" cy="8.2" r="1"/><circle cx="14.8" cy="8.6" r="1"/>',
  'user-plus': '<circle cx="9.5" cy="8" r="3.5"/><path d="M3.5 20a6 6 0 0 1 12 0"/><path d="M18 8.5v6"/><path d="M15 11.5h6"/>',
  'message-square': '<path d="M20 15.5a2 2 0 0 1-2 2H8l-4 3.5V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>',
  'shield-check': '<path d="M12 3l7 3v6c0 4.2-2.9 7.7-7 9-4.1-1.3-7-4.8-7-9V6z"/><path d="m9 12 2 2 4-4"/>',
  'hard-drive':
    '<path d="M5.5 13 7 6.6A1.6 1.6 0 0 1 8.6 5.5h6.8A1.6 1.6 0 0 1 17 6.6L18.5 13v4.4a1.6 1.6 0 0 1-1.6 1.6H7.1a1.6 1.6 0 0 1-1.6-1.6z"/><path d="M5.5 13h13"/><circle cx="8.4" cy="16.2" r=".9"/>',
  scale: '<path d="M12 3.5v17"/><path d="M7 20.5h10"/><path d="M4.5 7.5h15"/><path d="m4.5 7.5-2.5 6h5z"/><path d="m19.5 7.5 2.5 6h-5z"/>',
  'key-round': '<circle cx="8" cy="15.5" r="3.8"/><path d="m10.8 12.7 8.7-8.7"/><path d="m16.8 6.7 2.5 2.5"/>',
  phone:
    '<path d="M7 3.5h10A1.5 1.5 0 0 1 18.5 5v14a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M10.5 17.3h3"/>',
};

const inner = computed(() => ICONS[props.name] || ICONS.dot);
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    v-html="inner"
  />
</template>
