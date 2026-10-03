<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';
import { useAppStore } from '../../store';

const store = useAppStore();
const groups = ref<any[]>([]);
const fields = ref<any[]>([]);
const values = ref<Record<string, any>>({});
const dirty = ref<Record<string, any>>({});
const active = ref('site');
const keyword = ref('');
const loading = ref(true);
const saving = ref(false);

const visibleFields = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  if (term) {
    return fields.value.filter(
      (field) =>
        field.label.toLowerCase().includes(term) ||
        field.key.toLowerCase().includes(term) ||
        (field.description || '').toLowerCase().includes(term),
    );
  }
  return fields.value.filter((field) => field.group === active.value);
});

function current(field: any) {
  return field.key in dirty.value ? dirty.value[field.key] : values.value[field.key];
}

function setValue(field: any, value: any) {
  dirty.value = { ...dirty.value, [field.key]: value };
}

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>('/api/admin/settings');
    groups.value = data.groups || [];
    fields.value = data.fields || [];
    values.value = data.values || {};
    dirty.value = {};
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!Object.keys(dirty.value).length) {
    toast.info('没有需要保存的修改');
    return;
  }
  saving.value = true;
  try {
    const result = await api.put<any>('/api/admin/settings', { values: dirty.value });
    toast.success(`已保存 ${result.changed.length} 项设置`);
    values.value = result.values;
    dirty.value = {};
    await store.loadMeta();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  } finally {
    saving.value = false;
  }
}

async function resetGroup() {
  const group = groups.value.find((item) => item.key === active.value);
  if (!window.confirm(`确定把「${group?.name}」的所有设置恢复默认值吗？`)) return;
  const keys = fields.value.filter((field) => field.group === active.value).map((field) => field.key);
  await api.post('/api/admin/settings/reset', { keys });
  toast.success('已恢复默认值');
  await load();
}

async function uploadImage(field: any, file: File) {
  const result = await api.upload<{ url: string }>('/api/upload/image', file);
  setValue(field, result.url);
  toast.success('图片已上传，记得保存');
}

onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中…</p>
  <div v-else class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">系统设置</h1>
      <div class="flex items-center gap-2">
        <input v-model="keyword" class="input !w-56" placeholder="搜索设置项…" />
        <button class="btn-ghost text-xs" @click="resetGroup">恢复本组默认</button>
        <button class="btn-primary text-xs" :disabled="saving" @click="save">
          保存修改{{ Object.keys(dirty).length ? `（${Object.keys(dirty).length}）` : '' }}
        </button>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[200px_1fr]">
      <nav class="card h-fit p-2">
        <button
          v-for="group in groups"
          :key="group.key"
          class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm"
          :class="active === group.key && !keyword ? 'bg-primary/10 font-medium text-primary' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'"
          @click="active = group.key; keyword = ''"
        >
          <span>{{ group.name }}</span>
          <span class="text-[11px] text-slate-400">{{ fields.filter((field) => field.group === group.key).length }}</span>
        </button>
      </nav>

      <section class="card">
        <header class="border-b border-slate-100 px-4 py-3 text-sm dark:border-slate-800">
          {{ keyword ? `搜索结果（${visibleFields.length}）` : groups.find((group) => group.key === active)?.description }}
        </header>
        <div class="grid gap-4 p-4 md:grid-cols-2">
          <div
            v-for="field in visibleFields"
            :key="field.key"
            :class="field.type === 'json' || field.type === 'text' ? 'md:col-span-2' : ''"
          >
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ field.label }}</span>
              <code class="text-[11px] text-slate-400">{{ field.key }}</code>
              <span v-if="field.public" class="rounded bg-emerald-100 px-1 text-[10px] text-emerald-700 dark:bg-emerald-500/20">前台可见</span>
            </div>
            <p v-if="field.description" class="mb-1 text-[11px] text-slate-400">{{ field.description }}</p>

            <label v-if="field.type === 'boolean'" class="flex items-center gap-2 text-sm text-slate-500">
              <input
                type="checkbox"
                :checked="Boolean(current(field))"
                @change="(event) => setValue(field, (event.target as HTMLInputElement).checked)"
              />
              {{ current(field) ? '已启用' : '已关闭' }}
            </label>

            <select
              v-else-if="field.type === 'select'"
              class="input"
              :value="current(field)"
              @change="(event) => setValue(field, (event.target as HTMLSelectElement).value)"
            >
              <option v-for="option in field.options || []" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>

            <input
              v-else-if="field.type === 'number'"
              class="input"
              type="number"
              :min="field.min"
              :max="field.max"
              :value="current(field)"
              @input="(event) => setValue(field, Number((event.target as HTMLInputElement).value))"
            />

            <input
              v-else-if="field.type === 'color'"
              class="h-9 w-20 rounded border border-slate-200 bg-white"
              type="color"
              :value="current(field)"
              @input="(event) => setValue(field, (event.target as HTMLInputElement).value)"
            />

            <div v-else-if="field.type === 'image'" class="flex items-center gap-3">
              <img v-if="current(field)" :src="current(field)" class="h-12 w-24 rounded object-cover" alt="" />
              <label class="btn-ghost cursor-pointer text-xs">
                上传图片
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) uploadImage(field, file); }"
                />
              </label>
            </div>

            <textarea
              v-else-if="field.type === 'json' || field.type === 'text'"
              class="input min-h-[90px] font-mono text-xs"
              :value="typeof current(field) === 'string' ? current(field) : JSON.stringify(current(field), null, 2)"
              @input="(event) => setValue(field, (event.target as HTMLTextAreaElement).value)"
            ></textarea>

            <input
              v-else
              class="input"
              :type="field.type === 'password' ? 'password' : 'text'"
              :value="current(field)"
              @input="(event) => setValue(field, (event.target as HTMLInputElement).value)"
            />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
