<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import Icon from '../components/Icon.vue';

const store = useAppStore();
const router = useRouter();
const route = useRoute();
const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const providers = ref<any[]>([]);
const forgotOpen = ref(false);
const forgot = ref({ account: '', code: '', password: '', password2: '' });
const cooldown = ref(0);
const forgotError = ref('');

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

async function sendCode() {
  forgotError.value = '';
  if (!forgot.value.account.trim()) {
    forgotError.value = '请先填写用户名或邮箱';
    return;
  }
  try {
    const data = await api.post<any>('/api/auth/mail-code', { account: forgot.value.account.trim(), purpose: 'reset' });
    toast.success(data.masked ? `验证码已发送至 ${data.masked}` : '如果账号存在，验证码已发送');
    cooldown.value = 60;
    const timer = window.setInterval(() => {
      cooldown.value -= 1;
      if (cooldown.value <= 0) window.clearInterval(timer);
    }, 1000);
  } catch (err) {
    forgotError.value = err instanceof Error ? err.message : '发送失败';
  }
}

async function resetPassword() {
  forgotError.value = '';
  if (forgot.value.password !== forgot.value.password2) {
    forgotError.value = '两次输入的密码不一致';
    return;
  }
  try {
    await api.post('/api/auth/reset-password', {
      account: forgot.value.account.trim(),
      code: forgot.value.code.trim(),
      password: forgot.value.password,
      password2: forgot.value.password2,
    });
    toast.success('密码已重置，请用新密码登录');
    forgotOpen.value = false;
    forgot.value = { account: '', code: '', password: '', password2: '' };
  } catch (err) {
    forgotError.value = err instanceof Error ? err.message : '重置失败';
  }
}

function oauth(provider: string) {
  window.location.href = `/api/auth/oauth/${provider}/start?redirect=${encodeURIComponent(String(route.query.redirect || '/'))}`;
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
  <div class="mx-auto grid max-w-4xl gap-6 py-10 lg:grid-cols-2">
    <section class="surface flex flex-col justify-center p-8">
      <h1 class="bg-gradient-to-r from-[#6d4aff] to-[#22d3ee] bg-clip-text text-3xl font-black text-transparent">
        {{ store.siteName }}
      </h1>
      <p class="mt-3 text-sm muted">{{ store.settings.site_description || '开源微视频平台' }}</p>
      <ul class="mt-6 space-y-2 text-sm">
        <li class="flex items-center gap-2"><Icon name="check" :size="16" class="text-[var(--pv-accent)]" />投稿、弹幕、评论一站搞定</li>
        <li class="flex items-center gap-2"><Icon name="check" :size="16" class="text-[var(--pv-accent)]" />多清晰度播放与断点续播</li>
        <li class="flex items-center gap-2"><Icon name="check" :size="16" class="text-[var(--pv-accent)]" />关注、私信、直播与充电</li>
      </ul>
    </section>

    <form class="surface space-y-3 p-6" @submit.prevent="submit">
      <h2 class="text-lg font-semibold">登录</h2>
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

      <div v-if="providers.length" class="space-y-2 pt-2">
        <div class="flex items-center gap-2 text-xs muted">
          <span class="h-px flex-1 bg-[var(--pv-border)]"></span>第三方登录<span class="h-px flex-1 bg-[var(--pv-border)]"></span>
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <button
            v-for="item in providers"
            :key="item.id"
            type="button"
            class="btn-ghost text-xs"
            @click="oauth(item.id)"
          >
            <Icon name="key" :size="15" />{{ item.name }} 登录
          </button>
        </div>
      </div>

      <div class="flex items-center justify-between pt-1 text-xs">
        <button v-if="store.settings.mail_reset_enabled !== false" type="button" class="muted hover:text-[var(--pv-accent)]" @click="forgotOpen = true">
          忘记密码？
        </button>
        <p v-if="store.settings.allow_register !== false" class="muted">
          还没有账号？<RouterLink to="/register" class="link">立即注册</RouterLink>
        </p>
      </div>
    </form>

    <div v-if="forgotOpen" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="forgotOpen = false">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold"><Icon name="mail" :size="16" />通过邮箱找回密码</h3>
        <div><label class="label">用户名 / 邮箱</label><input v-model="forgot.account" class="input" /></div>
        <div>
          <label class="label">邮箱验证码</label>
          <div class="flex gap-2">
            <input v-model="forgot.code" class="input flex-1" placeholder="6 位数字" />
            <button type="button" class="btn-ghost shrink-0 text-xs" :disabled="cooldown > 0" @click="sendCode">
              {{ cooldown > 0 ? `${cooldown}s` : '发送验证码' }}
            </button>
          </div>
        </div>
        <div><label class="label">新密码</label><input v-model="forgot.password" type="password" class="input" /></div>
        <div><label class="label">确认新密码</label><input v-model="forgot.password2" type="password" class="input" /></div>
        <p v-if="forgotError" class="text-sm text-rose-500">{{ forgotError }}</p>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="forgotOpen = false">取消</button>
          <button class="btn-primary" @click="resetPassword">重置密码</button>
        </div>
      </div>
    </div>
  </div>
</template>
