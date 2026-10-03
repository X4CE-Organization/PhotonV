<script setup lang="ts">
import { onMounted } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import AppHeader from './components/AppHeader.vue';
import ToastHost from './components/ToastHost.vue';
import { useAppStore } from './store';

const store = useAppStore();
const route = useRoute();

onMounted(() => {
  void store.bootstrap();
});
</script>

<template>
  <div class="min-h-screen">
    <AppHeader />
    <main class="mx-auto max-w-[1440px] px-4 py-5">
      <RouterView :key="route.fullPath" />
    </main>
    <footer class="mt-10 border-t border-slate-200 py-6 text-center text-xs text-slate-400 dark:border-slate-800">
      <p>
        <a v-if="store.settings.github_url" :href="String(store.settings.github_url)" target="_blank" rel="noreferrer" class="hover:text-primary">
          {{ store.settings.footer_text || 'Powered by PhotonV' }}
        </a>
        <span v-else>{{ store.settings.footer_text || 'Powered by PhotonV' }}</span>
      </p>
      <p class="mt-1">
        <span>{{ store.settings.copyright || '© 2026 X4CE' }}</span>
        <span v-if="store.settings.beian"> · {{ store.settings.beian }}</span>
        <RouterLink to="/about" class="ml-2 hover:text-primary">关于本站</RouterLink>
      </p>
    </footer>
    <ToastHost />
  </div>
</template>
