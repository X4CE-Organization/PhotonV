<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { useAppStore, applyThemeColor } from '../store';
import { api } from '../api';
import { initials } from '../utils';
import { toast } from '../composables/toast';

const store = useAppStore();
const router = useRouter();
const keyword = ref('');
const menuOpen = ref(false);
const dark = ref(document.documentElement.classList.contains('dark'));
const categoriesOpen = ref(false);

const categories = computed(() => store.categories.slice(0, 10));

function submit() {
  const value = keyword.value.trim();
  if (!value) return;
  router.push({ name: 'search', query: { q: value } });
}

function toggleTheme() {
  dark.value = !dark.value;
  document.documentElement.classList.toggle('dark', dark.value);
  try {
    localStorage.setItem('photonv-theme', dark.value ? 'dark' : 'light');
  } catch {
    /* ignore */
  }
}

async function logout() {
  await store.logout();
  menuOpen.value = false;
  toast.success('已退出登录');
  router.push('/');
}

onMounted(() => {
  if (store.settings.theme_color) applyThemeColor(String(store.settings.theme_color));
});
</script>

<template>
  <header
    class="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95"
  >
    <div class="mx-auto flex h-14 max-w-[1440px] items-center gap-4 px-4">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2 text-lg font-extrabold text-primary">
        <img v-if="store.siteLogo" :src="store.siteLogo" alt="logo" class="h-7" />
        <span v-else class="grid h-7 w-7 place-items-center rounded-lg bg-primary text-sm text-white">P</span>
        <span>{{ store.siteName }}</span>
      </RouterLink>

      <nav class="hidden items-center gap-1 lg:flex">
        <RouterLink to="/" class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">首页</RouterLink>
        <div class="relative" @mouseenter="categoriesOpen = true" @mouseleave="categoriesOpen = false">
          <button class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
            频道 ▾
          </button>
          <div
            v-if="categoriesOpen"
            class="absolute left-0 top-full w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            <RouterLink
              v-for="item in categories"
              :key="item.slug"
              :to="`/category/${item.slug}`"
              class="flex items-center justify-between rounded-lg px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <span>{{ item.icon }} {{ item.name }}</span>
              <span class="text-xs text-slate-400">{{ item.count }}</span>
            </RouterLink>
          </div>
        </div>
        <RouterLink to="/rank" class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">排行榜</RouterLink>
        <RouterLink v-if="store.isLogin" to="/following" class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">关注</RouterLink>
        <RouterLink v-if="store.isLogin" to="/history" class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">历史</RouterLink>
        <RouterLink v-if="store.isLogin" to="/favorites" class="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">收藏</RouterLink>
      </nav>

      <form class="ml-auto hidden max-w-xs flex-1 md:block" @submit.prevent="submit">
        <input v-model="keyword" class="input" placeholder="搜索视频、用户" />
      </form>

      <button class="btn-ghost !px-2" :title="dark ? '切换到浅色' : '切换到深色'" @click="toggleTheme">
        {{ dark ? '☀' : '🌙' }}
      </button>

      <RouterLink v-if="store.isLogin" to="/upload" class="btn-primary !px-3">投稿</RouterLink>

      <RouterLink v-if="store.isLogin" to="/notifications" class="relative btn-ghost !px-2" title="消息">
        🔔
        <span
          v-if="store.unread > 0"
          class="absolute -right-1 -top-1 rounded-full bg-rose-500 px-1.5 text-[10px] text-white"
        >{{ store.unread }}</span>
      </RouterLink>

      <div v-if="store.isLogin" class="relative">
        <button class="flex items-center gap-2" @click="menuOpen = !menuOpen">
          <img v-if="store.user?.avatar" :src="store.user.avatar" class="h-8 w-8 rounded-full object-cover" alt="avatar" />
          <span v-else class="grid h-8 w-8 place-items-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
            {{ initials(store.user?.displayName || store.user?.username) }}
          </span>
          <span class="hidden text-sm sm:block">{{ store.user?.displayName }}</span>
        </button>
        <div
          v-if="menuOpen"
          class="absolute right-0 mt-2 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
          @click="menuOpen = false"
        >
          <div class="border-b border-slate-100 px-3 py-2 text-xs text-slate-500 dark:border-slate-800">
            Lv{{ store.user?.level }} · 硬币 {{ store.user?.coins }}
          </div>
          <RouterLink :to="`/space/${store.user?.username}`" class="block px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">个人空间</RouterLink>
          <RouterLink to="/upload" class="block px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">投稿管理</RouterLink>
          <RouterLink to="/settings" class="block px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">个人设置</RouterLink>
          <RouterLink v-if="store.isAdmin" to="/admin" class="block px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">管理后台</RouterLink>
          <button class="block w-full px-3 py-2 text-left text-sm text-rose-600 hover:bg-slate-50 dark:hover:bg-slate-800" @click="logout">
            退出登录
          </button>
        </div>
      </div>

      <template v-else>
        <RouterLink to="/login" class="btn-ghost">登录</RouterLink>
        <RouterLink v-if="store.settings.allow_register !== false" to="/register" class="btn-primary">注册</RouterLink>
      </template>
    </div>
  </header>
</template>
