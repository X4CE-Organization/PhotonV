<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatTime } from '../utils';

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

onMounted(fill);
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-4">
    <section class="card p-4">
      <h1 class="text-base font-semibold">个人资料</h1>
      <div class="mt-4 space-y-3">
        <div>
          <label class="label">昵称</label>
          <input v-model="form.display_name" class="input" />
        </div>
        <div>
          <label class="label">个性签名</label>
          <textarea v-model="form.bio" class="input min-h-[80px]" maxlength="500"></textarea>
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
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
        <div class="grid gap-3 sm:grid-cols-2">
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
        <div class="flex flex-wrap gap-4 text-sm text-slate-500">
          <label class="flex items-center gap-2"><input v-model="form.is_private" type="checkbox" />隐藏收藏与关注列表</label>
          <label class="flex items-center gap-2"><input v-model="form.allow_message" type="checkbox" />允许别人给我发私信</label>
          <label class="flex items-center gap-2"><input v-model="form.show_email" type="checkbox" />公开邮箱</label>
        </div>
        <div class="flex justify-end">
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存资料' }}</button>
        </div>
      </div>
    </section>

    <section class="card p-4">
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

    <section class="card p-4 text-sm">
      <h2 class="text-base font-semibold">账号信息</h2>
      <dl class="mt-3 space-y-2">
        <div class="flex justify-between"><dt class="text-slate-500">用户名</dt><dd>@{{ store.user?.username }}（{{ store.settings.allow_change_username ? '可修改' : '不可修改' }}）</dd></div>
        <div class="flex justify-between"><dt class="text-slate-500">硬币</dt><dd>{{ store.user?.coins }}</dd></div>
        <div class="flex justify-between"><dt class="text-slate-500">注册时间</dt><dd>{{ formatTime(store.user?.createdAt) }}</dd></div>
        <div class="flex justify-between"><dt class="text-slate-500">最近登录</dt><dd>{{ formatTime(store.user?.lastLoginAt) }}</dd></div>
      </dl>
    </section>
  </div>
</template>
