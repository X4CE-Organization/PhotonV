import { createRouter, createWebHistory } from 'vue-router';
import { useAppStore } from './store';

const routes = [
  { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
  { path: '/video/:id', name: 'video', component: () => import('./views/VideoView.vue') },
  { path: '/upload', name: 'upload', component: () => import('./views/UploadView.vue'), meta: { auth: true } },
  { path: '/category/:slug', name: 'category', component: () => import('./views/CategoryView.vue') },
  { path: '/search', name: 'search', component: () => import('./views/SearchView.vue') },
  { path: '/rank', name: 'rank', component: () => import('./views/RankView.vue') },
  { path: '/live', name: 'live', component: () => import('./views/LiveView.vue') },
  { path: '/live/:id', name: 'live-room', component: () => import('./views/LiveRoomView.vue') },
  { path: '/messages', name: 'messages', component: () => import('./views/MessagesView.vue'), meta: { auth: true } },
  { path: '/membership', name: 'membership', component: () => import('./views/MembershipView.vue') },
  { path: '/oauth/callback', name: 'oauth-callback', component: () => import('./views/OAuthCallbackView.vue') },
  { path: '/space/:username', name: 'space', component: () => import('./views/SpaceView.vue') },
  { path: '/history', name: 'history', component: () => import('./views/HistoryView.vue'), meta: { auth: true } },
  { path: '/favorites', name: 'favorites', component: () => import('./views/FavoritesView.vue'), meta: { auth: true } },
  { path: '/playlists', name: 'playlists', component: () => import('./views/PlaylistsView.vue'), meta: { auth: true } },
  { path: '/playlist/:id', name: 'playlist', component: () => import('./views/PlaylistView.vue') },
  { path: '/following', name: 'following', component: () => import('./views/FollowingView.vue'), meta: { auth: true } },
  { path: '/notifications', name: 'notifications', component: () => import('./views/NotificationsView.vue'), meta: { auth: true } },
  { path: '/settings', name: 'settings', component: () => import('./views/SettingsView.vue'), meta: { auth: true } },
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue') },
  { path: '/register', name: 'register', component: () => import('./views/RegisterView.vue') },
  { path: '/about', name: 'about', component: () => import('./views/AboutView.vue') },
  {
    path: '/admin',
    component: () => import('./views/admin/AdminLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('./views/admin/DashboardView.vue') },
      { path: 'users', name: 'admin-users', component: () => import('./views/admin/UsersView.vue') },
      { path: 'videos', name: 'admin-videos', component: () => import('./views/admin/VideosView.vue') },
      { path: 'comments', name: 'admin-comments', component: () => import('./views/admin/CommentsView.vue') },
      { path: 'categories', name: 'admin-categories', component: () => import('./views/admin/CategoriesView.vue') },
      { path: 'reports', name: 'admin-reports', component: () => import('./views/admin/ReportsView.vue') },
      { path: 'announcements', name: 'admin-announcements', component: () => import('./views/admin/AnnouncementsView.vue') },
      { path: 'carousel', name: 'admin-carousel', component: () => import('./views/admin/CarouselView.vue') },
      { path: 'live', name: 'admin-live', component: () => import('./views/admin/LivePanel.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('./views/admin/OrdersPanel.vue') },
      { path: 'infra', name: 'admin-infra', component: () => import('./views/admin/InfraPanel.vue'), meta: { superadmin: true } },
      { path: 'settings', name: 'admin-settings', component: () => import('./views/admin/SettingsView.vue'), meta: { superadmin: true } },
      { path: 'logs', name: 'admin-logs', component: () => import('./views/admin/LogsView.vue'), meta: { superadmin: true } },
      { path: 'maintenance', name: 'admin-maintenance', component: () => import('./views/admin/MaintenanceView.vue'), meta: { superadmin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('./views/NotFoundView.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(async (to) => {
  const store = useAppStore();
  if (store.loading) await store.bootstrap();
  if (to.meta.auth && !store.isLogin) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }
  if (to.meta.admin && !store.isAdmin) {
    return { name: 'not-found' };
  }
  return true;
});

export default router;
