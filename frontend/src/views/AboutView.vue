<script setup lang="ts">
import { useAppStore } from '../store';

const store = useAppStore();
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-4">
    <section class="surface p-6">
      <h1 class="text-xl font-bold">{{ store.settings.site_full_name || 'PhotonV 微视频平台' }}</h1>
      <p class="mt-3 whitespace-pre-wrap text-sm leading-relaxed">
        {{ store.settings.about_text }}
      </p>
      <p v-if="store.settings.github_url" class="mt-4 text-sm">
        开源仓库：
        <a :href="String(store.settings.github_url)" target="_blank" rel="noreferrer" class="link">
          {{ store.settings.github_url }}
        </a>
      </p>
      <p v-if="store.settings.contact_email" class="mt-2 text-sm muted">
        联系邮箱：{{ store.settings.contact_email }}
      </p>
    </section>

    <section class="surface p-6">
      <h2 class="text-base font-semibold">用户协议</h2>
      <p class="mt-2 whitespace-pre-wrap text-sm">{{ store.settings.user_agreement }}</p>
      <h2 class="mt-4 text-base font-semibold">隐私政策</h2>
      <p class="mt-2 whitespace-pre-wrap text-sm">{{ store.settings.privacy_policy }}</p>
      <h2 class="mt-4 text-base font-semibold">内容安全</h2>
      <p class="mt-2 whitespace-pre-wrap text-sm">{{ store.settings.content_security_note }}</p>
    </section>
  </div>
</template>
