<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import Icon from '../components/Icon.vue';

const store = useAppStore();
const router = useRouter();
const form = ref({ username: '', email: '', password: '', password2: '', invite_code: '', email_code: '' });
const loading = ref(false);
const error = ref('');
const cooldown = ref(0);
const providers = ref<any[]>([]);

async function sendCode() {
  error.value = '';
  if (!form.value.email.trim()) {
    error.value = '请先填写邮箱';
    return;
  }
  try {
    const data = await api.post<any>('/api/auth/mail-code', {
      account: form.value.email.trim(),
      purpose: 'verify',
    });
    toast.success(data.masked ? `验证码已发送至 ${data.masked}` : '验证码已发送');
    cooldown.value = 60;
    const timer = window.setInterval(() => {
      cooldown.value -= 1;
      if (cooldown.value <= 0) window.clearInterval(timer);
    }, 1000);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败';
  }
}

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

function oauth(provider: string) {
  window.location.href = `/api/auth/oauth/${provider}/start?redirect=%2F`;
}

onMounted(async () => {
  try {
    const data = await api.get<any>('/api/auth/oauth/providers');
    providers.value = data.showOnLogin ? data.items || [] : [];
  } catch {
    providers.value = [];
  }
});
</script>

<template>
  <div class="mx-auto max-w-md space-y-4 py-8">
    <h1 class="text-center text-2xl font-bold">注册 {{ store.siteName }}</h1>
    <form class="surface space-y-3 p-6" @submit.prevent="submit">
      <div>
        <label class="label">用户名</label>
        <input v-model="form.username" class="input" placeholder="3-20 个字符" />
      </div>
      <div>
        <label class="label">邮箱 {{ store.settings.register_need_email || store.settings.mail_register_verify ? '' : '（可选）' }}</label>
        <input v-model="form.email" class="input" placeholder="you@example.com" />
      </div>
      <div v-if="store.settings.mail_register_verify">
        <label class="label">邮箱验证码</label>
        <div class="flex gap-2">
          <input v-model="form.email_code" class="input flex-1" placeholder="6 位数字" />
          <button type="button" class="btn-ghost shrink-0 text-xs" :disabled="cooldown > 0" @click="sendCode">
            {{ cooldown > 0 ? `${cooldown}s` : '发送验证码' }}
          </button>
        </div>
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

      <div v-if="providers.length" class="grid gap-2 pt-1 sm:grid-cols-2">
        <button v-for="item in providers" :key="item.id" type="button" class="btn-ghost text-xs" @click="oauth(item.id)">
          <Icon name="key" :size="15" />{{ item.name }} 注册
        </button>
      </div>

      <p class="text-center text-xs muted">
        已有账号？<RouterLink to="/login" class="link">去登录</RouterLink>
      </p>
    </form>
  </div>
</template>
