<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { useAppStore } from '../../store';
import Icon from '../../components/Icon.vue';

const store = useAppStore();
const route = useRoute();

const sections = computed(() => [
  {
    title: '概览',
    items: [{ to: '/admin', label: '控制面板', icon: 'dashboard', exact: true }],
  },
  {
    title: '运营',
    items: [
      { to: '/admin/videos', label: '视频审核', icon: 'film' },
      { to: '/admin/comments', label: '评论弹幕', icon: 'message' },
      { to: '/admin/reports', label: '举报处理', icon: 'flag' },
      { to: '/admin/users', label: '用户管理', icon: 'users' },
      { to: '/admin/categories', label: '分区标签', icon: 'tag' },
      { to: '/admin/announcements', label: '公告管理', icon: 'info' },
      { to: '/admin/carousel', label: '首页轮播', icon: 'video' },
      { to: '/admin/live', label: '直播管理', icon: 'radio' },
      { to: '/admin/orders', label: '订单与会员', icon: 'card' },
    ],
  },
  {
    title: '系统',
    items: [
      { to: '/admin/settings', label: '系统设置', icon: 'settings', superadmin: true },
      { to: '/admin/logs', label: '操作日志', icon: 'file', superadmin: true },
      { to: '/admin/infra', label: '缓存与转码', icon: 'server', superadmin: true },
      { to: '/admin/maintenance', label: '备份与维护', icon: 'database', superadmin: true },
    ],
  },
]);

function visible(item: any) {
  return !item.superadmin || store.isSuperadmin;
}

function active(to: string, exact?: boolean) {
  return exact ? route.path === to : route.path === to || route.path.startsWith(`${to}/`);
}
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-[200px_1fr]">
    <aside class="card h-fit space-y-3 p-3">
      <div class="px-2 text-xs text-slate-400">管理后台</div>
      <div v-for="section in sections" :key="section.title">
        <div class="px-2 py-1 text-[11px] text-slate-400">{{ section.title }}</div>
        <RouterLink
          v-for="item in section.items.filter(visible)"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm"
          :class="active(item.to, (item as any).exact) ? 'bg-primary/10 font-medium text-primary' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'"
        >
          <Icon :name="item.icon" :size="17" />{{ item.label }}
        </RouterLink>
      </div>
      <RouterLink to="/" class="block rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">← 返回前台</RouterLink>
    </aside>
    <div><RouterView /></div>
  </div>
</template>
