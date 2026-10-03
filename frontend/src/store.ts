import { defineStore } from 'pinia';
import { api, setToken } from './api';

export interface SiteUser {
  id: number;
  username: string;
  displayName: string;
  avatar: string;
  bio?: string;
  level: number;
  exp?: number;
  coins?: number;
  role?: string;
  followerCount?: number;
  followingCount?: number;
  videoCount?: number;
  likeCount?: number;
  playCount?: number;
  isAdmin?: boolean;
  isSuperadmin?: boolean;
  isPrivate?: boolean;
  allowMessage?: boolean;
  showEmail?: boolean;
  email?: string;
  theme?: string;
  gender?: number;
  birthday?: string;
  banner?: string;
  createdAt?: string;
  lastLoginAt?: string;
  membershipLevel?: number;
  membershipExpires?: string | null;
  membershipActive?: boolean;
  totalEarned?: number;
  canLive?: boolean;
  emailVerified?: boolean;
  mailOptout?: boolean;
  streamKey?: string;
}

export const useAppStore = defineStore('app', {
  state: () => ({
    user: null as SiteUser | null,
    unread: 0,
    settings: {} as Record<string, any>,
    categories: [] as any[],
    hotTags: [] as any[],
    loading: true,
  }),
  getters: {
    isLogin: (state) => Boolean(state.user),
    isAdmin: (state) => Boolean(state.user?.isAdmin || state.user?.isSuperadmin),
    isSuperadmin: (state) => Boolean(state.user?.isSuperadmin),
    siteName: (state) => String(state.settings.site_name || 'PhotonV'),
    siteLogo: (state) => String(state.settings.site_logo || ''),
  },
  actions: {
    async bootstrap() {
      this.loading = true;
      try {
        await this.loadMeta();
        await this.refresh();
      } finally {
        this.loading = false;
      }
    },
    async loadMeta() {
      try {
        const data = await api.get<any>('/api/meta');
        this.settings = data.settings || {};
        this.categories = data.categories || [];
        this.hotTags = data.hotTags || [];
        if (this.settings.theme_color) {
          applyThemeColor(String(this.settings.theme_color));
        }
      } catch {
        /* ignore */
      }
    },
    async refresh() {
      try {
        const data = await api.get<{ user: SiteUser | null; unread: number }>('/api/auth/me');
        this.user = data.user;
        this.unread = data.unread || 0;
      } catch {
        this.user = null;
      }
    },
    applyUser(user: SiteUser | null) {
      this.user = user;
    },
    async login(username: string, password: string) {
      const data = await api.post<{ token: string; user: SiteUser | null }>('/api/auth/login', { username, password });
      setToken(data.token);
      this.user = data.user;
      // 兜底：万一接口没带上用户信息，用 /api/auth/me 补一次，避免调用方读到 null
      if (!this.user) await this.refresh();
      return this.user;
    },
    async register(payload: Record<string, unknown>) {
      const data = await api.post<{ token: string; user: SiteUser | null }>('/api/auth/register', payload);
      setToken(data.token);
      this.user = data.user;
      if (!this.user) await this.refresh();
      return this.user;
    },
    async logout() {
      try {
        await api.post('/api/auth/logout');
      } catch {
        /* ignore */
      }
      setToken(null);
      this.user = null;
    },
  },
});

export function applyThemeColor(hex: string): void {
  const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim());
  if (!match) return;
  const [r, g, b] = [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)];
  document.documentElement.style.setProperty('--photonv-primary', `${r} ${g} ${b}`);
  document.documentElement.style.setProperty(
    '--photonv-primary-soft',
    `${Math.min(255, Math.round(r + (255 - r) * 0.75))} ${Math.min(
      255,
      Math.round(g + (255 - g) * 0.75),
    )} ${Math.min(255, Math.round(b + (255 - b) * 0.75))}`,
  );
}
