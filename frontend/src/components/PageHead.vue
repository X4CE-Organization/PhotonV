<script setup lang="ts">
import Icon from './Icon.vue';

defineProps<{ icon?: string; title: string; subtitle?: string }>();
</script>

<template>
  <header class="pv-page-head">
    <span v-if="icon" class="pv-page-head-icon">
      <Icon :name="icon" :size="18" />
    </span>
    <div class="min-w-0">
      <h1 class="pv-page-head-title">{{ title }}</h1>
      <p v-if="subtitle" class="pv-page-head-sub">{{ subtitle }}</p>
    </div>
    <div class="ml-auto flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
