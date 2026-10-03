<script setup lang="ts">
import { ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';

const store = useAppStore();
const router = useRouter();
const route = useRoute();
const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function submit() {
  error.value = '';
  loading.value = true;
  try {
    const user = await store.login(username.value.trim(), password.value);
    toast.success(`欢迎回来，${user.displayName}`);
    router.push(String(route.query.redirect || '/'));
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-md space-y-4 py-10">
    <div class="text-center">
      <h1 class="text-2xl font-bold text-primary">{{ store.siteName }}</h1>
      <p class="mt-1 text-sm text-slate-500">登录后即可投稿、发弹幕、收藏与关注</p>
    </div>
    <form class="card space-y-3 p-6" @submit.prevent="submit">
      <div>
        <label class="label">用户名</label>
        <input v-model="username" class="input" autocomplete="username" placeholder="请输入用户名" />
      </div>
      <div>
        <label class="label">密码</label>
        <input v-model="password" type="password" class="input" autocomplete="current-password" placeholder="请输入密码" />
      </div>
      <p v-if="error" class="text-sm text-rose-500">{{ error }}</p>
      <button class="btn-primary w-full" :disabled="loading">{{ loading ? '登录中…' : '登录' }}</button>
      <p v-if="store.settings.allow_register !== false" class="text-center text-xs text-slate-500">
        还没有账号？<RouterLink to="/register" class="link ml-1">立即注册</RouterLink>
      </p>
    </form>
  </div>
</template>
