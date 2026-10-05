<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatTime, fromNow } from '../utils';
import Icon from '../components/Icon.vue';
import PageHead from '../components/PageHead.vue';

const store = useAppStore();
const form = ref({
  display_name: '',
  bio: '',
  avatar: '',
  banner: '',
  gender: 0,
  birthday: '',
  email: '',
  is_private: false,
  allow_message: true,
  show_email: false,
});
const password = ref({ old_password: '', new_password: '', new_password2: '' });
const saving = ref(false);
const savingPassword = ref(false);
const avatarInput = ref<HTMLInputElement | null>(null);
const mailPref = ref<any>(null);
const bindings = ref<{ bindings: any[]; providers: any[] } | null>(null);
const phoneInfo = ref<any>(null);
const phoneForm = ref({ phone: '', code: '' });
const phoneCooldown = ref(0);
const loginLogs = ref<any[]>([]);
const loginIps = ref(0);

async function loadLoginLogs() {
  try {
    const data = await api.get<any>('/api/auth/login-logs?limit=30');
    loginLogs.value = data.items || [];
    loginIps.value = data.distinctIps || 0;
  } catch {
    loginLogs.value = [];
  }
}

async function loadPhone() {
  try {
    phoneInfo.value = await api.get<any>('/api/me/phone');
  } catch {
    phoneInfo.value = null;
  }
}

async function sendPhoneCode() {
  if (!phoneForm.value.phone.trim()) {
    toast.error('请先填写手机号');
    return;
  }
  try {
    await api.post('/api/auth/sms-code', { phone: phoneForm.value.phone.trim(), purpose: 'bind' });
    toast.success('验证码已发送');
    phoneCooldown.value = 60;
    const timer = window.setInterval(() => {
      phoneCooldown.value -= 1;
      if (phoneCooldown.value <= 0) window.clearInterval(timer);
    }, 1000);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '发送失败');
  }
}

async function bindPhone() {
  try {
    await api.put('/api/me/phone', { phone: phoneForm.value.phone.trim(), code: phoneForm.value.code.trim() });
    toast.success('手机号已绑定');
    phoneForm.value = { phone: '', code: '' };
    await loadPhone();
    await store.refresh();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '绑定失败');
  }
}

async function unbindPhone() {
  if (!window.confirm('确定解绑手机号吗？')) return;
  try {
    await api.del('/api/me/phone');
    toast.success('已解绑');
    await loadPhone();
    await store.refresh();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '解绑失败');
  }
}

async function loadExtras() {
  try {
    mailPref.value = await api.get<any>('/api/me/mail-preference');
  } catch {
    mailPref.value = null;
  }
  try {
    bindings.value = await api.get<any>('/api/auth/oauth/bindings');
  } catch {
    bindings.value = null;
  }
}

async function toggleMail(optout: boolean) {
  await api.put('/api/me/mail-preference', { optout });
  if (mailPref.value) mailPref.value.optout = optout;
  toast.success(optout ? '已退订邮件通知' : '已开启邮件通知');
}

function bindProvider(provider: string) {
  window.location.href = `/api/auth/oauth/${provider}/start?bind=1`;
}

async function unbind(provider: string) {
  if (!window.confirm('确定解绑该第三方账号吗？')) return;
  await api.del(`/api/auth/oauth/${provider}`);
  toast.success('已解绑');
  void loadExtras();
}

function fill() {
  const user = store.user;
  if (!user) return;
  form.value = {
    display_name: user.displayName || '',
    bio: user.bio || '',
    avatar: user.avatar || '',
    banner: user.banner || '',
    gender: user.gender ?? 0,
    birthday: user.birthday || '',
    email: user.email || '',
    is_private: Boolean(user.isPrivate),
    allow_message: user.allowMessage !== false,
    show_email: Boolean(user.showEmail),
  };
}

async function save() {
  saving.value = true;
  try {
    const data = await api.put<any>('/api/auth/profile', form.value);
    store.applyUser(data.user);
    toast.success('资料已保存');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  } finally {
    saving.value = false;
  }
}

async function changePassword() {
  savingPassword.value = true;
  try {
    await api.put('/api/auth/password', password.value);
    password.value = { old_password: '', new_password: '', new_password2: '' };
    toast.success('密码已修改');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '修改失败');
  } finally {
    savingPassword.value = false;
  }
}

async function uploadAvatar(file: File) {
  const result = await api.upload<{ url: string }>('/api/upload/avatar', file);
  form.value.avatar = result.url;
  toast.success('头像已上传，记得保存');
}

async function uploadBanner(file: File) {
  const result = await api.upload<{ url: string }>('/api/upload/image', file);
  form.value.banner = result.url;
  toast.success('横幅已上传，记得保存');
}

onMounted(() => {
  fill();
  void loadExtras();
  void loadPhone();
  void loadLoginLogs();
});
</script>

<template>
  <div class="space-y-4">
    <PageHead icon="settings" title="个人设置" subtitle="资料、密码、通知、绑定与登录记录都在这里">
      <template #actions>
        <span class="chip text-[11px]">Lv{{ store.user?.level }} · 硬币 {{ store.user?.coins ?? 0 }}</span>
      </template>
    </PageHead>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-start">
      <!-- 左侧资料卡 -->
      <aside class="pv-settings-side">
        <img v-if="form.avatar" :src="form.avatar" class="h-20 w-20 rounded-2xl object-cover" alt="" />
        <span v-else class="grid h-20 w-20 place-items-center rounded-2xl bg-gradient-to-br from-[#6d4aff] to-[#22d3ee] text-2xl font-black text-white">
          {{ (form.display_name || store.user?.username || '?').slice(0, 1) }}
        </span>
        <p class="mt-3 text-sm font-semibold">{{ form.display_name || store.user?.username }}</p>
        <p class="text-[11px] muted">@{{ store.user?.username }}</p>
        <p class="mt-2 line-clamp-3 text-[11px] muted">{{ form.bio || '这个人很神秘，什么都没写' }}</p>
        <div class="mt-4 space-y-1.5 text-[11px] muted">
          <p class="flex justify-between"><span>经验</span><span>{{ store.user?.exp ?? 0 }}</span></p>
          <p class="flex justify-between"><span>会员</span><span>{{ store.user?.membershipActive ? '生效中' : '未开通' }}</span></p>
          <p class="flex justify-between"><span>手机号</span><span>{{ phoneInfo?.bound ? '已绑定' : '未绑定' }}</span></p>
          <p class="flex justify-between"><span>邮箱</span><span>{{ form.email ? '已填' : '未填' }}</span></p>
        </div>
        <RouterLink to="/membership" class="btn-ghost mt-4 w-full justify-center text-xs">会员中心</RouterLink>
      </aside>

      <div class="space-y-4">
    <section class="surface p-4">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="user" :size="17" />个人资料</h2>
      <div class="mt-4 space-y-3">
        <div>
          <label class="label">昵称</label>
          <input v-model="form.display_name" class="input" />
        </div>
        <div>
          <label class="label">个性签名</label>
          <textarea v-model="form.bio" class="input min-h-[80px]" maxlength="500"></textarea>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label class="label">头像</label>
            <div class="flex items-center gap-3">
              <img v-if="form.avatar" :src="form.avatar" class="h-14 w-14 rounded-full object-cover" alt="" />
              <button class="btn-ghost" @click="avatarInput?.click()">上传头像</button>
              <input
                ref="avatarInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) uploadAvatar(file); }"
              />
            </div>
          </div>
          <div>
            <label class="label">主页横幅</label>
            <div class="flex items-center gap-3">
              <img v-if="form.banner" :src="form.banner" class="h-14 w-24 rounded object-cover" alt="" />
              <label class="btn-ghost cursor-pointer">
                上传横幅
                <input type="file" accept="image/*" class="hidden" @change="(event) => { const file = (event.target as HTMLInputElement).files?.[0]; if (file) uploadBanner(file); }" />
              </label>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label class="label">邮箱</label>
            <input v-model="form.email" class="input" />
          </div>
          <div>
            <label class="label">生日</label>
            <input v-model="form.birthday" class="input" placeholder="2000-01-01" />
          </div>
        </div>
        <div>
          <label class="label">性别</label>
          <select v-model.number="form.gender" class="input">
            <option :value="0">保密</option>
            <option :value="1">男</option>
            <option :value="2">女</option>
          </select>
        </div>
        <div class="flex flex-wrap gap-4 text-sm muted">
          <label class="flex items-center gap-2"><input v-model="form.is_private" type="checkbox" />隐藏收藏与关注列表</label>
          <label class="flex items-center gap-2"><input v-model="form.allow_message" type="checkbox" />允许别人给我发私信</label>
          <label class="flex items-center gap-2"><input v-model="form.show_email" type="checkbox" />公开邮箱</label>
        </div>
        <div class="flex justify-end">
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存资料' }}</button>
        </div>
      </div>
    </section>

    <section class="surface p-4">
      <h2 class="text-base font-semibold">修改密码</h2>
      <div class="mt-4 space-y-3">
        <div><label class="label">原密码</label><input v-model="password.old_password" type="password" class="input" /></div>
        <div><label class="label">新密码</label><input v-model="password.new_password" type="password" class="input" /></div>
        <div><label class="label">确认新密码</label><input v-model="password.new_password2" type="password" class="input" /></div>
        <div class="flex justify-end">
          <button class="btn-primary" :disabled="savingPassword" @click="changePassword">修改密码</button>
        </div>
      </div>
    </section>

    <section class="surface p-4 text-sm">
      <h2 class="text-base font-semibold">账号信息</h2>
      <dl class="mt-3 space-y-2">
        <div class="flex justify-between"><dt class="muted">用户名</dt><dd>@{{ store.user?.username }}（{{ store.settings.allow_change_username ? '可修改' : '不可修改' }}）</dd></div>
        <div class="flex justify-between"><dt class="muted">硬币</dt><dd>{{ store.user?.coins }}</dd></div>
        <div class="flex justify-between"><dt class="muted">注册时间</dt><dd>{{ formatTime(store.user?.createdAt) }}</dd></div>
        <div class="flex justify-between"><dt class="muted">最近登录</dt><dd>{{ formatTime(store.user?.lastLoginAt) }}</dd></div>
      </dl>
    </section>

    <section v-if="mailPref" class="surface p-4">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="mail" :size="17" />邮件通知</h2>
      <p class="mt-2 text-xs muted">
        {{ mailPref.enabled ? `回复、投币、订单等通知可以发送到 ${mailPref.email || '你的邮箱'}。` : '本站暂未开启邮件服务，通知只会出现在站内信里。' }}
      </p>
      <label class="mt-3 flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          :checked="!mailPref.optout"
          :disabled="!mailPref.enabled"
          @change="toggleMail(!(($event.target as HTMLInputElement).checked))"
        />
        接收邮件通知
      </label>
      <p v-if="!mailPref.email" class="mt-2 text-xs text-amber-500">还没有填写邮箱，请先在上方「个人资料」里补上。</p>
    </section>

    <section v-if="bindings?.providers?.length" class="surface p-4">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="key" :size="17" />第三方账号绑定</h2>
      <ul class="mt-3 divide-y divide-[var(--pv-border)] text-sm">
        <li v-for="provider in bindings.providers" :key="provider.id" class="flex items-center gap-3 py-2.5">
          <span>{{ provider.name }}</span>
          <span v-if="bindings.bindings.find((item) => item.provider === provider.id)" class="chip text-[11px]">
            已绑定 {{ bindings.bindings.find((item) => item.provider === provider.id)?.username }}
          </span>
          <span class="ml-auto">
            <button
              v-if="bindings.bindings.find((item) => item.provider === provider.id)"
              class="text-xs text-rose-500 hover:underline"
              @click="unbind(provider.id)"
            >
              解绑
            </button>
            <button v-else class="text-xs text-[var(--pv-accent)] hover:underline" @click="bindProvider(provider.id)">去绑定</button>
          </span>
        </li>
      </ul>
    </section>

    <section class="surface p-4 text-sm">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="radio" :size="17" />直播与会员</h2>
      <dl class="mt-3 space-y-2">
        <div class="flex justify-between"><dt class="muted">直播权限</dt><dd>{{ store.user?.canLive ? '已开通' : '未开通（联系管理员）' }}</dd></div>
        <div class="flex justify-between">
          <dt class="muted">会员状态</dt>
          <dd>{{ store.user?.membershipActive ? `已开通 · 到期 ${formatTime(store.user?.membershipExpires)}` : '未开通' }}</dd>
        </div>
        <div class="flex justify-between"><dt class="muted">收到充电</dt><dd>{{ store.user?.totalEarned ?? 0 }} 硬币</dd></div>
      </dl>
      <RouterLink to="/membership" class="btn-ghost mt-3 text-xs">前往会员中心</RouterLink>
    </section>

    <section class="surface p-4 text-sm">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="phone" :size="17" />手机号</h2>
      <template v-if="phoneInfo?.bound">
        <div class="mt-3 flex items-center gap-3">
          <span class="font-medium">{{ phoneInfo.phone }}</span>
          <span v-if="phoneInfo.verified" class="chip text-[11px]">已验证</span>
          <button class="ml-auto text-xs text-rose-500 hover:underline" @click="unbindPhone">解绑</button>
        </div>
        <p class="mt-2 text-xs muted">解绑后无法使用手机号 + 验证码登录。</p>
      </template>
      <template v-else>
        <p class="mt-2 text-xs muted">
          绑定后可以用手机号 + 验证码登录{{ phoneInfo?.smsEnabled ? '' : '（当前是开发模式，验证码会写进日志与站内信）' }}。
        </p>
        <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <input v-model="phoneForm.phone" class="input" placeholder="11 位手机号" />
          <input v-model="phoneForm.code" class="input" placeholder="验证码" />
          <button class="btn-ghost text-xs" :disabled="phoneCooldown > 0" @click="sendPhoneCode">
            {{ phoneCooldown > 0 ? `${phoneCooldown}s` : '发送验证码' }}
          </button>
        </div>
        <div class="mt-3 flex justify-end">
          <button class="btn-primary text-xs" @click="bindPhone">绑定手机号</button>
        </div>
      </template>
    </section>

    <section class="surface p-4 text-sm">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="clock" :size="17" />登录记录</h2>
      <p class="mt-2 text-xs muted">
        最近 {{ loginLogs.length }} 次登录，共出现过 {{ loginIps }} 个不同 IP。
        发现不是自己的登录时，请立刻修改密码。
      </p>
      <div v-if="loginLogs.length" class="mt-3 space-y-1.5">
        <div
          v-for="item in loginLogs"
          :key="item.id"
          class="flex flex-wrap items-center gap-3 rounded-xl bg-[var(--pv-surface-2)] px-3 py-2 text-xs"
        >
          <span class="font-mono">{{ item.ip || '未知 IP' }}</span>
          <span class="chip !py-0 text-[10px]" :class="item.success ? '' : '!text-rose-500'">
            {{ item.success ? '成功' : '失败' }}
          </span>
          <span class="min-w-0 flex-1 truncate muted">{{ item.userAgent || '未知设备' }}</span>
          <span class="muted">{{ fromNow(item.createdAt) }}</span>
        </div>
      </div>
      <p v-else class="mt-3 text-xs muted">暂时没有登录记录。</p>
    </section>
      </div>
    </div>
  </div>
</template>
