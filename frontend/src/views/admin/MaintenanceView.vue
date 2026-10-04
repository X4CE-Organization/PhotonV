<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';
import { formatSize, fromNow } from '../../utils';

const backups = ref<any[]>([]);
const busy = ref(false);
const system = ref<any>(null);

async function load() {
  const [backupData, health] = await Promise.all([
    api.get<any>('/api/admin/backups'),
    api.get<any>('/api/health'),
  ]);
  backups.value = backupData.items || [];
  system.value = health;
}

async function createBackup() {
  busy.value = true;
  try {
    const result = await api.post<any>('/api/admin/backups');
    toast.success(`备份完成：${result.file}`);
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '备份失败');
  } finally {
    busy.value = false;
  }
}

async function removeBackup(item: any) {
  if (!window.confirm(`确定删除备份 ${item.file} 吗？`)) return;
  await api.del(`/api/admin/backups/${item.file}`);
  toast.success('已删除');
  void load();
}

async function cleanup() {
  busy.value = true;
  try {
    const result = await api.post<any>('/api/admin/maintenance/cleanup');
    toast.success(`已清理登录日志 ${result.removedLoginLogs} 条、限流记录 ${result.removedRateLimits} 条`);
  } finally {
    busy.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-base font-semibold">备份与维护</h1>

    <section class="surface p-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="text-sm font-semibold">数据库备份</h2>
          <p class="mt-1 text-xs muted">
            使用 pg_dump 导出完整数据库到 data/backups，恢复时执行 psql -f 文件即可。
          </p>
        </div>
        <button class="btn-primary text-xs" :disabled="busy" @click="createBackup">
          {{ busy ? '处理中…' : '立即备份' }}
        </button>
      </div>
      <ul class="mt-3 divide-y divide-[var(--pv-border)] text-sm">
        <li v-for="item in backups" :key="item.file" class="flex items-center gap-3 py-2">
          <span class="font-mono text-xs">{{ item.file }}</span>
          <span class="text-xs muted">{{ formatSize(item.size) }}</span>
          <span class="ml-auto text-xs muted">{{ fromNow(item.created_at) }}</span>
          <button class="text-xs text-rose-500 hover:underline" @click="removeBackup(item)">删除</button>
        </li>
        <li v-if="!backups.length" class="py-4 text-xs muted">还没有备份文件</li>
      </ul>
    </section>

    <section class="surface p-4">
      <h2 class="text-sm font-semibold">数据清理</h2>
      <p class="mt-1 text-xs muted">清理过期的登录日志与限流记录，保留天数在「系统设置 → 备份与维护」里调整。</p>
      <button class="btn-ghost mt-3 text-xs" :disabled="busy" @click="cleanup">立即清理</button>
    </section>

    <section class="surface p-4 text-sm">
      <h2 class="text-sm font-semibold">运行状态</h2>
      <dl class="mt-3 space-y-2">
        <div class="flex justify-between"><dt class="muted">服务</dt><dd>{{ system?.name }} v{{ system?.version }}</dd></div>
        <div class="flex justify-between">
          <dt class="muted">健康检查</dt>
          <dd :class="system?.ok ? 'text-emerald-600' : 'text-rose-500'">{{ system?.ok ? '正常' : '异常' }}</dd>
        </div>
        <div class="flex justify-between"><dt class="muted">备份数量</dt><dd>{{ backups.length }}</dd></div>
      </dl>
    </section>
  </div>
</template>
