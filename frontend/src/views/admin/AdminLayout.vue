<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { useAppStore } from '../../store';
import Icon from '../../components/Icon.vue';

const store = useAppStore();
const route = useRoute();

interface ConsoleItem {
  to: string;
  label: string;
  icon: string;
  desc: string;
  superadmin?: boolean;
  exact?: boolean;
}

interface ConsoleGroup {
  key: string;
  title: string;
  hint: string;
  items: ConsoleItem[];
}

const groups: ConsoleGroup[] = [
  {
    key: 'overview',
    title: '总览',
    hint: '一眼看清站点现状',
    items: [{ to: '/admin', label: '运行总览', icon: 'dashboard', desc: '关键指标与待办', exact: true }],
  },
  {
    key: 'content',
    title: '内容',
    hint: '投稿、分区、直播与首页位',
    items: [
      { to: '/admin/videos', label: '视频审核', icon: 'film', desc: '通过 / 驳回 / 精选置顶' },
      { to: '/admin/comments', label: '评论弹幕', icon: 'message', desc: '检索并清理内容' },
      { to: '/admin/categories', label: '分区标签', icon: 'tag', desc: '频道与标签维护' },
      { to: '/admin/announcements', label: '公告管理', icon: 'info', desc: '站内公告与置顶' },
      { to: '/admin/carousel', label: '首页轮播', icon: 'video', desc: '首页大图位管理' },
      { to: '/admin/live', label: '直播管理', icon: 'radio', desc: '开播权限与状态' },
    ],
  },
  {
    key: 'people',
    title: '用户',
    hint: '账号、举报与交易',
    items: [
      { to: '/admin/users', label: '用户管理', icon: 'users', desc: '角色 / 封禁 / 硬币' },
      { to: '/admin/reports', label: '举报处理', icon: 'flag', desc: '审核与处置' },
      { to: '/admin/orders', label: '订单与会员', icon: 'card', desc: '收款确认与套餐' },
    ],
  },
  {
    key: 'system',
    title: '系统',
    hint: '设置、日志与运维',
    items: [
      { to: '/admin/settings', label: '系统设置', icon: 'settings', desc: '全站参数在线调整', superadmin: true },
      { to: '/admin/logs', label: '操作日志', icon: 'file', desc: '谁改了什么', superadmin: true },
      { to: '/admin/infra', label: '缓存与转码', icon: 'server', desc: 'Redis / ffmpeg / 队列', superadmin: true },
      { to: '/admin/maintenance', label: '备份与维护', icon: 'database', desc: '备份与清理', superadmin: true },
    ],
  },
];

const visibleGroups = computed(() =>
  groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.superadmin || store.isSuperadmin),
    }))
    // 普通管理员看不到系统分组时，直接把空分组去掉，不留一个点不开的标签
    .filter((group) => group.items.length > 0),
);

function groupOf(path: string): string {
  for (const group of groups) {
    if (group.items.some((item) => (item.exact ? path === item.to : path.startsWith(item.to)))) {
      return group.key;
    }
  }
  return 'overview';
}

const activeGroup = ref(groupOf(route.path));
watch(
  () => route.path,
  (path) => {
    activeGroup.value = groupOf(path);
  },
);

const currentGroup = computed(
  () => visibleGroups.value.find((group) => group.key === activeGroup.value) || visibleGroups.value[0],
);

function isActive(item: ConsoleItem): boolean {
  return item.exact ? route.path === item.to : route.path === item.to || route.path.startsWith(`${item.to}/`);
}

const roleLabel = computed(() => (store.isSuperadmin ? '超级管理员' : '管理员'));
</script>

<template>
  <div class="space-y-4">
    <header class="pv-console-head">
      <div class="pv-console-glow"></div>
      <div class="relative flex flex-wrap items-center gap-4">
        <span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white/10 ring-1 ring-white/20">
          <Icon name="shield" :size="21" />
        </span>
        <div class="min-w-0">
          <p class="font-mono text-[10px] uppercase tracking-[0.28em] text-white/45">photonv console</p>
          <h1 class="text-lg font-semibold leading-tight">管理控制台</h1>
        </div>
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <span class="rounded-full bg-white/10 px-3 py-1 text-[11px] ring-1 ring-white/15">
            {{ store.siteName }} · {{ roleLabel }} · @{{ store.user?.username }}
          </span>
          <RouterLink
            to="/"
            class="rounded-full bg-white/95 px-3.5 py-1.5 text-[11px] font-semibold text-slate-900 transition hover:bg-white"
          >
            回到前台
          </RouterLink>
        </div>
      </div>

      <div class="relative mt-5 flex flex-wrap gap-1.5">
        <button
          v-for="group in visibleGroups"
          :key="group.key"
          class="pv-console-group"
          :class="activeGroup === group.key ? 'is-active' : ''"
          @click="activeGroup = group.key"
        >
          {{ group.title }}
          <span class="ml-1 text-[10px] opacity-60">{{ group.items.length }}</span>
        </button>
      </div>
    </header>

    <nav class="pv-console-modules">
      <span class="hidden shrink-0 items-center gap-1.5 pr-2 text-[11px] text-slate-400 lg:flex">
        <Icon name="compass" :size="13" />{{ currentGroup?.hint }}
      </span>
      <RouterLink
        v-for="item in currentGroup?.items || []"
        :key="item.to"
        :to="item.to"
        class="pv-console-module"
        :class="isActive(item) ? 'is-active' : ''"
        :title="item.desc"
      >
        <Icon :name="item.icon" :size="15" />
        <span class="font-medium">{{ item.label }}</span>
        <span class="hidden text-[11px] opacity-60 xl:inline">{{ item.desc }}</span>
      </RouterLink>
    </nav>

    <div class="pv-console-body">
      <RouterView />
    </div>
  </div>
</template>
