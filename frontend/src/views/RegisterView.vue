<script setup lang="ts">
import { ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';

const store = useAppStore();
const router = useRouter();
const form = ref({ username: '', email: '', password: '', password2: '', invite_code: '' });
const loading = ref(false);
const error = ref('');

async function submit() {
  error.value = '';
  if (form.value.password !== form.value.password2) {
    error.value = '两次输入的密码不一致';
    return;
  }
  loading.value = true;
  try {
    const user = await store.register(form.value);
    toast.success(`注册成功，欢迎 ${user.displayName}`);
    router.push('/');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-md space-y-4 py-10">
    <h1 class="text-center text-2xl font-bold text-primary">注册 {{ store.siteName }}</h1>
    <form class="card space-y-3 p-6" @submit.prevent="submit">
      <div>
        <label class="label">用户名</label>
        <input v-model="form.username" class="input" placeholder="3-20 个字符" />
      </div>
      <div>
        <label class="label">邮箱 {{ store.settings.register_need_email ? '' : '（可选）' }}</label>
        <input v-model="form.email" class="input" placeholder="you@example.com" />
      </div>
      <div>
        <label class="label">密码</label>
        <input v-model="form.password" type="password" class="input" />
      </div>
      <div>
        <label class="label">确认密码</label>
        <input v-model="form.password2" type="password" class="input" />
      </div>
      <div v-if="store.settings.register_need_invite">
        <label class="label">邀请码</label>
        <input v-model="form.invite_code" class="input" />
      </div>
      <p v-if="error" class="text-sm text-rose-500">{{ error }}</p>
      <button class="btn-primary w-full" :disabled="loading">{{ loading ? '注册中…' : '注册' }}</button>
      <p class="text-center text-xs text-slate-500">
        已有账号？<RouterLink to="/login" class="link ml-1">去登录</RouterLink>
      </p>
    </form>
  </div>
</template>
