<script setup lang="ts">
import { onMounted } from 'vue';
import AppShell from './components/AppShell.vue';
import { useAppStore } from './store';

const store = useAppStore();

onMounted(() => {
  void store.bootstrap();
});
</script>

<template>
  <AppShell />
</template>
