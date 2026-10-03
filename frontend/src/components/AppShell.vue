<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { useAppStore, applyThemeColor } from '../store';
import { api } from '../api';
import { initials } from '../utils';
import { toast } from '../composables/toast';
import Icon from './Icon.vue';
import ToastHost from './ToastHost.vue';

const store = useAppStore();
const router = useRouter();
const route = useRoute();
const keyword = ref('');
const menuOpen = ref(false);
const collapsed = ref(false);
const mobileMenu = ref(false);
const dark = ref(document.documentElement.classList.contains('dark'));
const dmUnread = ref(0);
let socket: WebSocket | null = null;
let timer = 0;

const navItems = computed(() => [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/category/anime', label: '频道', icon: 'compass', match: '/category' },
  { to: '/live', label: '直播', icon: 'radio' },
  { to: '/rank', label: '排行榜', icon: 'flame' },
  { to: '/following', label: '关注', icon: 'users', auth: true },
  { to: '/favorites', label: '收藏', icon: 'bookmark', auth: true },
  { to: '/playlists', label: '合集', icon: 'list', auth: true },
  { to: '/history', label: '历史', icon: 'history', auth: true },
  { to: '/messages', label: '私信', icon: 'message', auth: true, badge: dmUnread },
  { to: '/membership', label: '会员', icon: 'crown' },
]);

const visibleNav = computed(() => navItems.value.filter((item) => !item.auth || store.isLogin));
const badgeOf = (item: any): number => (item.badge ? Number(item.badge.value) : 0);

function isActive(to: string, match?: string) {
  const target = match || to;
  return target === '/' ? route.path === '/' : route.path.startsWith(target);
}

function submit() {
  const value = keyword.value.trim();
  if (!value) return;
  router.push({ name: 'search', query: { q: value } });
  mobileMenu.value = false;
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
  socket?.close();
  toast.success('已退出登录');
  router.push('/');
}

function connectSocket() {
  socket?.close();
  if (!store.isLogin) return;
  const token = localStorage.getItem('photonv-token') || '';
  if (!token) return;
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  try {
    socket = new WebSocket(`${protocol}://${location.host}/ws/messages?token=${encodeURIComponent(token)}`);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'hello') dmUnread.value = data.unread || 0;
        if (data.event === 'message') {
          dmUnread.value += 1;
          toast.info(`${data.from?.displayName || '有人'} 给你发了私信`);
        }
      } catch {
        /* ignore */
      }
    };
    socket.onclose = () => {
      socket = null;
    };
  } catch {
    socket = null;
  }
}

onMounted(async () => {
  if (store.settings.theme_color) applyThemeColor(String(store.settings.theme_color));
  if (store.isLogin) {
    try {
      const data = await api.get<{ unread: number }>('/api/messages/unread');
      dmUnread.value = data.unread || 0;
    } catch {
      /* ignore */
    }
    connectSocket();
  }
  timer = window.setInterval(() => {
    if (store.isLogin && !socket) connectSocket();
  }, 15000);
});

onUnmounted(() => {
  window.clearInterval(timer);
  socket?.close();
});
</script>

<template>
  <div class="min-h-screen">
    <div class="mx-auto flex max-w-[1600px] gap-4 px-3 pb-16 pt-3 lg:px-5 lg:pb-3">
      <!-- 左侧导航（桌面） -->
      <aside
        class="sticky top-3 hidden h-[calc(100vh-24px)] shrink-0 flex-col rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-3 transition-all lg:flex"
        :class="collapsed ? 'w-[76px]' : 'w-[208px]'"
      >
        <RouterLink to="/" class="mb-4 flex items-center gap-2.5 px-1.5 py-1">
          <img v-if="store.siteLogo" :src="store.siteLogo" alt="logo" class="h-8 w-8 rounded-xl object-cover" />
          <span v-else class="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-sm font-black text-white">
            P
          </span>
          <span v-if="!collapsed" class="text-lg font-extrabold tracking-tight">{{ store.siteName }}</span>
        </RouterLink>

        <nav class="flex-1 space-y-1">
          <RouterLink
            v-for="item in visibleNav"
            :key="item.to"
            :to="item.to"
            class="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition"
            :class="isActive(item.to, (item as any).match)
              ? 'bg-gradient-to-r from-[#6d4aff]/25 to-transparent font-semibold text-[var(--pv-accent)]'
              : 'muted hover:bg-[var(--pv-surface-2)] hover:text-[var(--pv-text)]'"
          >
            <Icon :name="item.icon" :size="19" />
            <span v-if="!collapsed">{{ item.label }}</span>
            <span
              v-if="badgeOf(item) > 0"
              class="ml-auto rounded-full bg-rose-500 px-1.5 text-[10px] font-semibold text-white"
            >
              {{ badgeOf(item) > 99 ? '99+' : badgeOf(item) }}
            </span>
          </RouterLink>
        </nav>

        <div class="space-y-1 border-t border-[var(--pv-border)] pt-2">
          <RouterLink
            v-if="store.isLogin"
            to="/upload"
            class="flex items-center gap-3 rounded-xl bg-gradient-to-r from-[#6d4aff] to-[#22d3ee] px-3 py-2.5 text-sm font-semibold text-white"
          >
            <Icon name="upload" :size="19" />
            <span v-if="!collapsed">投稿</span>
          </RouterLink>
          <button class="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm muted hover:bg-[var(--pv-surface-2)]" @click="collapsed = !collapsed">
            <Icon name="list" :size="19" />
            <span v-if="!collapsed">收起导航</span>
          </button>
        </div>
      </aside>

      <!-- 主区域 -->
      <div class="min-w-0 flex-1">
        <header class="sticky top-0 z-30 mb-4 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)]/95 px-3 py-2.5 backdrop-blur">
          <div class="flex items-center gap-3">
            <button class="rounded-xl p-2 lg:hidden" @click="mobileMenu = !mobileMenu">
              <Icon name="menu" />
            </button>
            <RouterLink to="/" class="flex items-center gap-2 lg:hidden">
              <span class="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-xs font-black text-white">P</span>
              <span class="font-bold">{{ store.siteName }}</span>
            </RouterLink>

            <form class="relative ml-auto hidden max-w-xl flex-1 md:block" @submit.prevent="submit">
              <Icon name="search" :size="17" class="pointer-events-none absolute left-3 top-2.5 muted" />
              <input v-model="keyword" class="input !pl-10" placeholder="搜索视频、UP 主、直播" />
            </form>

            <div class="ml-auto flex items-center gap-1.5 md:ml-0">
              <button class="rounded-xl p-2 muted hover:bg-[var(--pv-surface-2)]" :title="dark ? '浅色模式' : '深色模式'" @click="toggleTheme">
                <Icon :name="dark ? 'sun' : 'moon'" :size="19" />
              </button>
              <RouterLink v-if="store.isLogin" to="/notifications" class="relative rounded-xl p-2 muted hover:bg-[var(--pv-surface-2)]" title="通知">
                <Icon name="bell" :size="19" />
                <span v-if="store.unread > 0" class="absolute right-0.5 top-0.5 h-2 w-2 rounded-full bg-rose-500"></span>
              </RouterLink>
              <RouterLink v-if="store.isLogin" to="/upload" class="btn-primary !px-3 !py-1.5 text-xs">
                <Icon name="upload" :size="15" />投稿
              </RouterLink>

              <div v-if="store.isLogin" class="relative">
                <button class="flex items-center gap-2 rounded-xl p-1 hover:bg-[var(--pv-surface-2)]" @click="menuOpen = !menuOpen">
                  <img v-if="store.user?.avatar" :src="store.user.avatar" class="h-8 w-8 rounded-full object-cover" alt="" />
                  <span v-else class="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-xs font-bold text-white">
                    {{ initials(store.user?.displayName || store.user?.username) }}
                  </span>
                  <Icon v-if="!mobileMenu" name="chevron-down" :size="15" class="hidden muted sm:block" />
                </button>
                <div
                  v-if="menuOpen"
                  class="absolute right-0 z-40 mt-2 w-56 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-1.5"
                  @click="menuOpen = false"
                >
                  <div class="px-3 py-2 text-xs muted">
                    Lv{{ store.user?.level }} · 硬币 {{ store.user?.coins }}
                    <span v-if="store.user?.membershipActive" class="ml-1 rounded-full bg-gradient-to-r from-[#6d4aff] to-[#22d3ee] px-1.5 py-0.5 text-[10px] font-semibold text-white">
                      {{ store.settings.membership_badge_text || '会员' }}
                    </span>
                  </div>
                  <RouterLink :to="`/space/${store.user?.username}`" class="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-[var(--pv-surface-2)]">
                    <Icon name="user" :size="16" />个人空间
                  </RouterLink>
                  <RouterLink to="/membership" class="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-[var(--pv-surface-2)]">
                    <Icon name="crown" :size="16" />会员 / 充电
                  </RouterLink>
                  <RouterLink to="/settings" class="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-[var(--pv-surface-2)]">
                    <Icon name="settings" :size="16" />设置
                  </RouterLink>
                  <RouterLink v-if="store.isAdmin" to="/admin" class="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-[var(--pv-surface-2)]">
                    <Icon name="dashboard" :size="16" />管理后台
                  </RouterLink>
                  <button class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-rose-500 hover:bg-[var(--pv-surface-2)]" @click="logout">
                    <Icon name="logout" :size="16" />退出登录
                  </button>
                </div>
              </div>

              <template v-else>
                <RouterLink to="/login" class="btn-ghost !px-3 !py-1.5 text-xs">登录</RouterLink>
                <RouterLink v-if="store.settings.allow_register !== false" to="/register" class="btn-primary !px-3 !py-1.5 text-xs">注册</RouterLink>
              </template>
            </div>
          </div>

          <nav v-if="mobileMenu" class="mt-3 grid grid-cols-3 gap-2 lg:hidden">
            <RouterLink
              v-for="item in visibleNav"
              :key="item.to"
              :to="item.to"
              class="flex items-center gap-2 rounded-xl bg-[var(--pv-surface-2)] px-3 py-2 text-sm"
              @click="mobileMenu = false"
            >
              <Icon :name="item.icon" :size="16" />{{ item.label }}
            </RouterLink>
          </nav>
        </header>

        <main>
          <RouterView :key="route.fullPath" />
        </main>

        <footer class="mt-10 border-t border-[var(--pv-border)] pt-5 text-center text-xs muted">
          <p>
            <a v-if="store.settings.github_url" :href="String(store.settings.github_url)" target="_blank" rel="noreferrer" class="hover:text-[var(--pv-accent)]">
              {{ store.settings.footer_text || 'Powered by PhotonV' }}
            </a>
            <span v-else>{{ store.settings.footer_text || 'Powered by PhotonV' }}</span>
          </p>
          <p class="mt-1">
            {{ store.settings.copyright || '© 2026 X4CE' }}
            <span v-if="store.settings.beian"> · {{ store.settings.beian }}</span>
            <RouterLink to="/about" class="ml-2 hover:text-[var(--pv-accent)]">关于本站</RouterLink>
          </p>
        </footer>
      </div>
    </div>

    <ToastHost />
  </div>
</template>
