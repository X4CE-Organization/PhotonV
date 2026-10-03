<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { useAppStore } from '../../store';
import Icon from '../../components/Icon.vue';

const store = useAppStore();
const route = useRoute();

interface ConsoleItem {
  to: string;
  label: string;
  icon: string;
  superadmin?: boolean;
  exact?: boolean;
}

interface ConsoleGroup {
  title: string;
  items: ConsoleItem[];
}

const groups: ConsoleGroup[] = [
  {
    title: '总览',
    items: [{ to: '/admin', label: '运行总览', icon: 'dashboard', exact: true }],
  },
  {
    title: '内容',
    items: [
      { to: '/admin/videos', label: '视频审核', icon: 'film' },
      { to: '/admin/comments', label: '评论弹幕', icon: 'message' },
      { to: '/admin/categories', label: '分区标签', icon: 'tag' },
      { to: '/admin/announcements', label: '公告', icon: 'info' },
      { to: '/admin/carousel', label: '轮播', icon: 'video' },
      { to: '/admin/live', label: '直播', icon: 'radio' },
    ],
  },
  {
    title: '用户',
    items: [
      { to: '/admin/users', label: '用户管理', icon: 'users' },
      { to: '/admin/reports', label: '举报处理', icon: 'flag' },
      { to: '/admin/orders', label: '订单与会员', icon: 'card' },
    ],
  },
  {
    title: '系统',
    items: [
      { to: '/admin/settings', label: '系统设置', icon: 'settings', superadmin: true },
      { to: '/admin/logs', label: '日志', icon: 'file', superadmin: true },
      { to: '/admin/infra', label: '缓存与转码', icon: 'server', superadmin: true },
      { to: '/admin/maintenance', label: '备份维护', icon: 'database', superadmin: true },
    ],
  },
];

const visibleGroups = computed(() =>
  groups
    .map((group) => ({ ...group, items: group.items.filter((item) => !item.superadmin || store.isSuperadmin) }))
    .filter((group) => group.items.length > 0),
);

function isActive(item: ConsoleItem): boolean {
  return item.exact ? route.path === item.to : route.path === item.to || route.path.startsWith(`${item.to}/`);
}

const current = computed(() => {
  for (const group of visibleGroups.value) {
    const hit = group.items.find(isActive);
    if (hit) return hit;
  }
  return null;
});

const roleLabel = computed(() => (store.isSuperadmin ? '超级管理员' : '管理员'));
</script>

<template>
  <div class="pv-console">
    <!-- 一行标题栏：左边说明现在在哪，右边是身份与出口 -->
    <header class="pv-console-bar">
      <span class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--pv-surface-2)] text-[var(--pv-accent)]">
        <Icon name="shield" :size="17" />
      </span>
      <div class="min-w-0">
        <p class="text-[13px] font-semibold leading-tight">管理控制台</p>
        <p class="truncate text-[11px] muted">{{ current ? current.label : '运行总览' }} · {{ store.siteName }}</p>
      </div>
      <div class="ml-auto flex shrink-0 items-center gap-2">
        <span class="chip !py-0.5 text-[11px]">{{ roleLabel }} · @{{ store.user?.username }}</span>
        <RouterLink to="/" class="btn-ghost !px-3 !py-1.5 text-xs">回到前台</RouterLink>
      </div>
    </header>

    <!-- 一行标签栏，分组之间用竖线隔开 -->
    <nav class="pv-console-tabs">
      <template v-for="(group, index) in visibleGroups" :key="group.title">
        <span v-if="index > 0" class="pv-console-sep"></span>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="pv-console-tab"
          :class="isActive(item) ? 'is-active' : ''"
        >
          <Icon :name="item.icon" :size="15" />{{ item.label }}
        </RouterLink>
      </template>
    </nav>

    <div class="pv-console-body">
      <RouterView />
    </div>
  </div>
</template>
