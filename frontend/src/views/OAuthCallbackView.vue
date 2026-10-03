<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { setToken } from '../api';
import { useAppStore } from '../store';
import Icon from '../components/Icon.vue';

const router = useRouter();
const store = useAppStore();
const status = ref<'working' | 'ok' | 'error'>('working');
const message = ref('');

onMounted(async () => {
  const params = new URLSearchParams(location.search);
  const token = params.get('token');
  const bound = params.get('bound');
  const error = params.get('error');
  const redirect = params.get('redirect') || '/';

  if (error) {
    status.value = 'error';
    message.value = error;
    return;
  }
  if (token) {
    setToken(token);
    await store.refresh();
    status.value = 'ok';
    message.value = '登录成功，正在跳转…';
    history.replaceState({}, '', '/oauth/callback');
    setTimeout(() => router.replace(redirect), 800);
    return;
  }
  if (bound) {
    await store.refresh();
    status.value = 'ok';
    message.value = `已成功绑定 ${bound} 账号`;
    history.replaceState({}, '', '/oauth/callback');
    setTimeout(() => router.replace('/settings'), 900);
    return;
  }
  status.value = 'error';
  message.value = '回调参数不完整';
});
</script>

<template>
  <div class="mx-auto max-w-md py-24 text-center">
    <div
      class="mx-auto grid h-14 w-14 place-items-center rounded-2xl"
      :class="status === 'ok' ? 'bg-emerald-500/15 text-emerald-500' : status === 'error' ? 'bg-rose-500/15 text-rose-500' : 'bg-[var(--pv-surface-2)] muted'"
    >
      <Icon :name="status === 'ok' ? 'check' : status === 'error' ? 'close' : 'refresh'" :size="24" />
    </div>
    <p class="mt-4 text-sm">{{ message || '正在处理第三方登录…' }}</p>
    <div v-if="status === 'error'" class="mt-5 flex justify-center gap-2">
      <RouterLink to="/login" class="btn-primary">返回登录</RouterLink>
      <RouterLink to="/" class="btn-ghost">回到首页</RouterLink>
    </div>
  </div>
</template>
