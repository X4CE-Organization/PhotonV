<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '../../api';
import { toast } from '../../composables/toast';
import { useAppStore } from '../../store';
import Icon from '../../components/Icon.vue';

const store = useAppStore();
const groups = ref<any[]>([]);
const fields = ref<any[]>([]);
const values = ref<Record<string, any>>({});
const dirty = ref<Record<string, any>>({});
const keyword = ref('');
const loading = ref(true);
const saving = ref(false);
const activeGroup = ref('');
const failedUploads = ref<Record<string, string>>({});

const sectionRefs = ref<Record<string, HTMLElement | null>>({});

function setSectionRef(key: string, el: any) {
  sectionRefs.value[key] = el as HTMLElement | null;
}

/** 每个分组 + 它的设置项，按注册顺序 */
const sections = computed(() =>
  groups.value
    .map((group) => ({ ...group, fields: fields.value.filter((field) => field.group === group.key) }))
    .filter((group) => group.fields.length > 0),
);

/** 搜索时退化成一条平铺结果列表，并标出它属于哪个分组 */
const searchResult = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  if (!term) return [];
  return fields.value
    .map((field) => ({ field, group: groups.value.find((g) => g.key === field.group) }))
    .filter(({ field, group }) => {
      // 设置项的名称 / 键名 / 说明，以及它所属分组的名称与描述，都参与匹配
      const haystack = [
        field.label,
        field.key,
        field.description || '',
        group?.name || '',
        group?.description || '',
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(term);
    })
});

const dirtyCount = computed(() => Object.keys(dirty.value).length);

function groupName(key: string): string {
  return groups.value.find((item) => item.key === key)?.name || key;
}

function current(field: any) {
  return field.key in dirty.value ? dirty.value[field.key] : values.value[field.key];
}

function isDirty(field: any): boolean {
  return field.key in dirty.value;
}

function setValue(field: any, value: any) {
  dirty.value = { ...dirty.value, [field.key]: value };
  if (field.type === 'json') validateJson(field, value);
}

function validateJson(field: any, value: any) {
  const next = { ...failedUploads.value };
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  try {
    JSON.parse(text);
    delete next[field.key];
  } catch {
    next[field.key] = 'JSON 格式不对，保存前先修正';
  }
  failedUploads.value = next;
}

function jsonText(field: any): string {
  const value = current(field);
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function controlWidth(field: any): string {
  if (field.type === 'json' || field.type === 'text') return 'w-full';
  if (field.type === 'image') return 'w-full sm:w-auto';
  return 'w-full sm:w-72';
}

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>('/api/admin/settings');
    groups.value = data.groups || [];
    fields.value = data.fields || [];
    values.value = data.values || {};
    dirty.value = {};
    failedUploads.value = {};
    activeGroup.value = groups.value[0]?.key || '';
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!dirtyCount.value) {
    toast.info('没有需要保存的修改');
    return;
  }
  if (Object.keys(failedUploads.value).length) {
    toast.error('有设置项格式不正确，先修正再保存');
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

function discard() {
  dirty.value = {};
  failedUploads.value = {};
  toast.info('已放弃未保存的修改');
}

async function resetGroup(key: string) {
  if (!window.confirm(`把「${groupName(key)}」恢复成默认值？`)) return;
  const keys = fields.value.filter((field) => field.group === key).map((field) => field.key);
  await api.post('/api/admin/settings/reset', { keys });
  toast.success(`「${groupName(key)}」已恢复默认`);
  await load();
}

async function uploadImage(field: any, file: File) {
  try {
    const result = await api.upload<{ url: string }>('/api/upload/image', file);
    setValue(field, result.url);
    toast.success('图片已上传，记得点保存');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '上传失败');
  }
}

function goTo(key: string) {
  keyword.value = '';
  activeGroup.value = key;
  void nextTick(() => {
    sectionRefs.value[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

/** 滚动时高亮左侧对应的分组 */
function onScroll() {
  if (keyword.value) return;
  const entries = Object.entries(sectionRefs.value).filter(([, el]) => el) as [string, HTMLElement][];
  if (!entries.length) return;
  const line = 150;
  let currentKey = entries[0][0];
  for (const [key, el] of entries) {
    if (el.getBoundingClientRect().top <= line) currentKey = key;
  }
  if (currentKey !== activeGroup.value) activeGroup.value = currentKey;
}

onMounted(async () => {
  await load();
  window.addEventListener('scroll', onScroll, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll);
});
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>

  <div v-else class="pv-settings">
    <!-- 顶部：标题 + 搜索 + 操作 -->
    <div class="pv-settings-head">
      <div class="min-w-0">
        <h1 class="text-base font-semibold">系统设置</h1>
        <p class="mt-0.5 text-[11px] muted">
          共 {{ sections.length }} 组 · {{ fields.length }} 项，改完记得保存
        </p>
      </div>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <div class="relative">
          <input v-model="keyword" class="input !w-52 !pl-8 !py-1.5 text-xs" placeholder="搜索设置项…" />
          <Icon name="search" :size="14" class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 opacity-50" />
        </div>
        <button class="btn-ghost !py-1.5 text-xs" @click="resetGroup(activeGroup)" :disabled="!activeGroup || Boolean(keyword)">
          本组恢复默认
        </button>
        <button class="btn-primary !py-1.5 text-xs" :disabled="saving || !dirtyCount" @click="save">
          保存修改{{ dirtyCount ? `（${dirtyCount}）` : '' }}
        </button>
      </div>
    </div>

    <!-- 搜索结果 -->
    <template v-if="keyword">
      <div class="pv-settings-panel">
        <p class="pv-settings-panel-head">
          搜索「{{ keyword }}」命中 {{ searchResult.length }} 项
        </p>
        <p v-if="!searchResult.length" class="px-5 py-10 text-center text-sm muted">没有匹配的设置项</p>
        <div
          v-for="row in searchResult"
          :key="row.field.key"
          class="pv-setting-row"
          :class="isDirty(row.field) ? 'is-dirty' : ''"
        >
          <div class="pv-setting-info">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-medium">{{ row.field.label }}</span>
              <button class="chip !py-0 text-[10px] hover:!text-[var(--pv-accent)]" @click="goTo(row.field.group)">
                {{ row.group?.name }}
              </button>
            </div>
            <p v-if="row.field.description" class="mt-0.5 text-[11px] muted">{{ row.field.description }}</p>
          </div>
          <div class="pv-setting-control" :class="controlWidth(row.field)">
            <input
              v-if="row.field.type === 'boolean'"
              class="pv-switch"
              type="checkbox"
              :checked="Boolean(current(row.field))"
              @change="(e) => setValue(row.field, (e.target as HTMLInputElement).checked)"
            />
            <input
              v-else
              class="input !py-1.5 text-xs"
              :value="typeof current(row.field) === 'object' ? JSON.stringify(current(row.field)) : current(row.field)"
              @input="(e) => setValue(row.field, (e.target as HTMLInputElement).value)"
            />
          </div>
        </div>
      </div>
    </template>

    <!-- 正常浏览：左侧锚点导航 + 右侧分组设置 -->
    <div v-else class="pv-settings-body">
      <aside class="pv-settings-rail">
        <button
          v-for="group in sections"
          :key="group.key"
          class="pv-settings-rail-item"
          :class="activeGroup === group.key ? 'is-active' : ''"
          @click="goTo(group.key)"
        >
          <Icon :name="group.icon || 'settings'" :size="15" />
          <span class="truncate">{{ group.name }}</span>
          <span class="ml-auto text-[11px] opacity-60">{{ group.fields.length }}</span>
        </button>
      </aside>

      <div class="space-y-4">
        <section
          v-for="group in sections"
          :key="group.key"
          :ref="(el) => setSectionRef(group.key, el)"
          :data-group="group.key"
          class="pv-settings-panel scroll-mt-4"
        >
          <header class="pv-settings-panel-head flex items-center gap-2">
            <Icon :name="group.icon || 'settings'" :size="15" />
            <span class="font-medium">{{ group.name }}</span>
            <span class="muted">·</span>
            <span class="truncate text-[11px] font-normal muted">{{ group.description }}</span>
            <button class="ml-auto shrink-0 text-[11px] muted hover:text-[var(--pv-accent)]" @click="resetGroup(group.key)">
              恢复默认
            </button>
          </header>

          <div
            v-for="field in group.fields"
            :key="field.key"
            class="pv-setting-row"
            :class="isDirty(field) ? 'is-dirty' : ''"
          >
            <div class="pv-setting-info">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium">{{ field.label }}</span>
                <span v-if="field.public" class="chip !py-0 text-[10px] !text-emerald-600">前台可见</span>
                <span v-if="isDirty(field)" class="chip !py-0 text-[10px] !text-[var(--pv-accent)]">已改</span>
              </div>
              <p v-if="field.description" class="mt-0.5 text-[11px] muted">{{ field.description }}</p>
              <p v-if="failedUploads[field.key]" class="mt-0.5 text-[11px] text-rose-500">{{ failedUploads[field.key] }}</p>
              <code class="mt-0.5 block font-mono text-[10px] opacity-40">{{ field.key }}</code>
            </div>

            <div class="pv-setting-control" :class="controlWidth(field)">
              <!-- 开关 -->
              <label v-if="field.type === 'boolean'" class="inline-flex cursor-pointer items-center gap-2">
                <input
                  class="pv-switch"
                  type="checkbox"
                  :checked="Boolean(current(field))"
                  @change="(e) => setValue(field, (e.target as HTMLInputElement).checked)"
                />
                <span class="text-xs muted">{{ current(field) ? '已开启' : '已关闭' }}</span>
              </label>

              <!-- 下拉 -->
              <select
                v-else-if="field.type === 'select'"
                class="input !py-1.5 text-xs"
                :value="current(field)"
                @change="(e) => setValue(field, (e.target as HTMLSelectElement).value)"
              >
                <option v-for="option in field.options || []" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>

              <!-- 数字 -->
              <div v-else-if="field.type === 'number'" class="flex items-center gap-2">
                <input
                  class="input !py-1.5 text-xs"
                  type="number"
                  :min="field.min"
                  :max="field.max"
                  :value="current(field)"
                  @input="(e) => setValue(field, Number((e.target as HTMLInputElement).value))"
                />
                <span v-if="field.min !== undefined || field.max !== undefined" class="shrink-0 text-[10px] muted">
                  {{ field.min ?? '—' }} ~ {{ field.max ?? '—' }}
                </span>
              </div>

              <!-- 颜色 -->
              <div v-else-if="field.type === 'color'" class="flex items-center gap-2">
                <input
                  class="h-8 w-10 cursor-pointer rounded-lg border-0 bg-transparent p-0"
                  type="color"
                  :value="current(field)"
                  @input="(e) => setValue(field, (e.target as HTMLInputElement).value)"
                />
                <input
                  class="input !py-1.5 font-mono text-xs"
                  :value="current(field)"
                  @input="(e) => setValue(field, (e.target as HTMLInputElement).value)"
                />
              </div>

              <!-- 图片 -->
              <div v-else-if="field.type === 'image'" class="flex flex-wrap items-center gap-2">
                <img v-if="current(field)" :src="current(field)" class="h-10 w-20 rounded-lg border border-[var(--pv-border)] object-cover" alt="" />
                <span v-else class="grid h-10 w-20 place-items-center rounded-lg bg-[var(--pv-surface-2)] text-[10px] muted">无图</span>
                <label class="btn-ghost cursor-pointer !py-1.5 text-xs">
                  上传
                  <input
                    type="file"
                    accept="image/*"
                    class="hidden"
                    @change="(e) => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) uploadImage(field, f); }"
                  />
                </label>
                <button v-if="current(field)" class="text-[11px] text-rose-500 hover:underline" @click="setValue(field, '')">清除</button>
              </div>

              <!-- 长文本 / JSON -->
              <textarea
                v-else-if="field.type === 'json' || field.type === 'text'"
                class="input min-h-[80px] font-mono text-xs"
                :value="jsonText(field)"
                @input="(e) => setValue(field, (e.target as HTMLTextAreaElement).value)"
              ></textarea>

              <!-- 普通字符串 / 密码 -->
              <input
                v-else
                class="input !py-1.5 text-xs"
                :type="field.type === 'password' ? 'password' : 'text'"
                :value="current(field)"
                @input="(e) => setValue(field, (e.target as HTMLInputElement).value)"
              />
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 未保存提示条 -->
    <Transition name="fade">
      <div v-if="dirtyCount" class="pv-settings-dock">
        <span class="text-xs">有 <b>{{ dirtyCount }}</b> 项修改还没保存</span>
        <button class="btn-ghost !py-1.5 text-xs" @click="discard">放弃</button>
        <button class="btn-primary !py-1.5 text-xs" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
      </div>
    </Transition>
  </div>
</template>
