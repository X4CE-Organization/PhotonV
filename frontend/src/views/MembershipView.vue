<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api';
import { toast } from '../composables/toast';
import { useAppStore } from '../store';
import { formatTime } from '../utils';
import Icon from '../components/Icon.vue';

const store = useAppStore();
const plans = ref<any>(null);
const orders = ref<any[]>([]);
const membership = ref<any>(null);
const loading = ref(true);
const amount = ref(10);
const busy = ref(false);
const methods = ref<any[]>([]);
const payMethod = ref('manual');
const checkout = ref<any>(null);
const payState = ref<any>(null);
const pollTimer = ref<number | null>(null);

function stopPolling() {
  if (pollTimer.value) window.clearInterval(pollTimer.value);
  pollTimer.value = null;
}

async function startPolling(order: any) {
  stopPolling();
  pollTimer.value = window.setInterval(async () => {
    try {
      const status = await api.get<any>(`/api/payments/${order.id}/status`);
      payState.value = { ...payState.value, status: status.status };
      if (status.status === 'paid') {
        stopPolling();
        toast.success('支付成功，权益已到账');
        checkout.value = null;
        await load();
      }
    } catch {
      /* ignore */
    }
  }, Math.max(1, Number(store.settings.pay_poll_seconds || 3)) * 1000);
}

async function confirmPay() {
  if (!checkout.value) return;
  busy.value = true;
  try {
    const payload: any = { type: checkout.value.type, pay_method: payMethod.value };
    if (checkout.value.type === 'membership') payload.plan_id = checkout.value.plan.id;
    if (checkout.value.type === 'coins') payload.amount_cents = Math.round(checkout.value.amount * 100);
    const created = await api.post<any>('/api/orders', payload);
    const order = created.order;
    const payment = await api.post<any>(`/api/payments/${order.id}/create`, { method: payMethod.value });
    if (payment.method === 'manual') {
      payState.value = { mode: 'manual', message: payment.message, status: order.status, orderId: order.id };
    } else if (payment.mode === 'page') {
      window.open(payment.payUrl, '_blank');
      payState.value = { mode: 'page', payUrl: payment.payUrl, status: order.status, orderId: order.id };
      await startPolling(order);
    } else {
      payState.value = { mode: 'qr', qrUrl: payment.qrUrl, qrCode: payment.qrCode, status: order.status, orderId: order.id };
      await startPolling(order);
    }
    await load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '下单失败');
  } finally {
    busy.value = false;
  }
}

function closeCheckout() {
  stopPolling();
  checkout.value = null;
  payState.value = null;
}

async function load() {
  loading.value = true;
  try {
    plans.value = await api.get<any>('/api/plans');
    methods.value = (await api.get<any>('/api/payments/methods')).items || [];
    const firstEnabled = methods.value.find((item: any) => item.enabled);
    if (firstEnabled) payMethod.value = firstEnabled.id;
    if (store.isLogin) {
      try {
        const mine = await api.get<any>('/api/orders/mine');
        orders.value = mine.items || [];
        membership.value = await api.get<any>('/api/me/membership');
      } catch {
        /* ignore */
      }
    }
  } finally {
    loading.value = false;
  }
}

function requireLogin(): boolean {
  if (!store.isLogin) {
    toast.info('请先登录');
    return false;
  }
  return true;
}

async function buyMembership(plan: any) {
  if (!requireLogin()) return;
  checkout.value = { type: 'membership', plan, title: `开通${plan.name}`, amount: plan.priceYuan };
  payState.value = null;
}

async function recharge() {
  if (!requireLogin()) return;
  checkout.value = { type: 'coins', amount: Number(amount.value) || 0, title: `充值 ${Math.round(amount.value * plans.value.coinsPerYuan)} 硬币` };
  payState.value = null;
}

onMounted(load);
</script>

<template>
  <p v-if="loading" class="py-20 text-center text-sm muted">加载中…</p>
  <div v-else-if="plans" class="space-y-5">
    <section class="surface overflow-hidden">
      <div class="bg-gradient-to-r from-[#6d4aff] to-[#22d3ee] px-6 py-6 text-white">
        <h1 class="flex items-center gap-2 text-xl font-bold"><Icon name="crown" :size="22" />{{ plans.badgeText }}</h1>
        <p class="mt-2 max-w-2xl text-sm opacity-90">{{ plans.note }}</p>
        <div v-if="membership?.active" class="mt-3 inline-flex items-center gap-2 rounded-full bg-white/20 px-3 py-1 text-xs">
          <Icon name="check" :size="14" />已开通 · 到期 {{ formatTime(membership.expires) }}
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_340px]">
      <div class="space-y-4">
        <section class="surface p-4">
          <h2 class="text-sm font-semibold">会员套餐</h2>
          <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div
              v-for="plan in plans.items"
              :key="plan.id"
              class="rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface-2)] p-4 transition hover:border-[var(--pv-accent)]"
            >
              <div class="text-sm font-semibold">{{ plan.name }}</div>
              <div class="mt-2 text-2xl font-bold text-[var(--pv-accent)]">¥{{ plan.priceYuan }}</div>
              <p class="mt-2 min-h-[40px] text-xs muted">{{ plan.description }}</p>
              <button class="btn-primary mt-3 w-full text-xs" :disabled="busy || !plans.membershipEnabled" @click="buyMembership(plan)">
                {{ plan.days }} 天
              </button>
            </div>
            <p v-if="!plans.items.length" class="text-xs muted">还没有配置会员套餐</p>
          </div>
        </section>

        <section class="surface p-4">
          <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="coin" :size="16" />硬币充值</h2>
          <p class="mt-1 text-xs muted">当前比例：1 元 = {{ plans.coinsPerYuan }} 硬币。硬币可用于投币、充电与解锁会员。</p>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <div class="flex gap-2">
              <button v-for="value in [1, 5, 10, 50]" :key="value" class="chip !px-3 !py-1.5" :class="amount === value ? '!border-[var(--pv-accent)] !text-[var(--pv-accent)]' : ''" @click="amount = value">
                ¥{{ value }}
              </button>
            </div>
            <input v-model.number="amount" type="number" min="1" class="input !w-24" />
            <button class="btn-primary text-xs" :disabled="busy || !plans.rechargeEnabled" @click="recharge">
              充值 {{ Math.round(amount * plans.coinsPerYuan) }} 硬币
            </button>
          </div>
          <p v-if="plans.payManualNote" class="mt-3 rounded-xl bg-[var(--pv-surface-2)] p-3 text-xs muted">{{ plans.payManualNote }}</p>
        </section>

        <section class="surface p-4">
          <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="card" :size="16" />我的订单</h2>
          <table class="table-base mt-3">
            <thead><tr><th>订单号</th><th>内容</th><th class="w-24">金额</th><th class="w-24">状态</th><th class="w-32">时间</th></tr></thead>
            <tbody>
              <tr v-for="item in orders" :key="item.id">
                <td class="font-mono text-xs">{{ item.orderNo }}</td>
                <td class="text-sm">{{ item.title }}</td>
                <td class="text-xs">¥{{ (item.amountCents / 100).toFixed(2) }}</td>
                <td class="text-xs">
                  <span :class="item.status === 'paid' ? 'text-emerald-500' : item.status === 'pending' ? 'text-amber-500' : 'muted'">
                    {{ item.status === 'paid' ? '已支付' : item.status === 'pending' ? '待支付' : item.status === 'cancelled' ? '已取消' : '已退款' }}
                  </span>
                </td>
                <td class="text-xs muted">{{ formatTime(item.createdAt) }}</td>
              </tr>
              <tr v-if="!orders.length"><td colspan="5" class="py-6 text-center text-xs muted">还没有订单</td></tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside class="space-y-4">
        <section class="surface p-4 text-sm">
          <h2 class="text-sm font-semibold">我的资产</h2>
          <dl class="mt-3 space-y-2 text-sm">
            <div class="flex justify-between"><dt class="muted">硬币</dt><dd class="font-semibold">{{ membership?.coins ?? store.user?.coins ?? 0 }}</dd></div>
            <div class="flex justify-between"><dt class="muted">收到充电</dt><dd class="font-semibold">{{ membership?.totalEarned ?? 0 }}</dd></div>
            <div class="flex justify-between"><dt class="muted">会员状态</dt><dd>{{ membership?.active ? '已开通' : '未开通' }}</dd></div>
            <div class="flex justify-between"><dt class="muted">直播权限</dt><dd>{{ membership?.canLive ? '已开通' : '未开通' }}</dd></div>
          </dl>
          <RouterLink v-if="membership?.canLive" to="/live" class="btn-ghost mt-3 w-full text-xs">
            <Icon name="radio" :size="15" />去开播
          </RouterLink>
        </section>

        <section class="surface p-4 text-xs muted">
          <h2 class="mb-2 text-sm font-semibold text-[var(--pv-text)]">充电说明</h2>
          <p>在 UP 主主页或个人空间点「充电」，用硬币支持创作者。充电比例如下：</p>
          <p class="mt-2">当前比例：{{ plans.chargeRatio }} 硬币 = 1 元，创作者分成 {{ store.settings.creator_share_percent ?? 70 }}%。</p>
        </section>
      </aside>
    </div>
  </div>

    <div v-if="checkout" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="closeCheckout">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold"><Icon name="card" :size="16" />选择支付方式</h3>
        <p class="text-xs muted">{{ checkout.title }} · ¥{{ (checkout.type === 'membership' ? checkout.plan.priceYuan : checkout.amount).toFixed(2) }}</p>

        <div class="grid gap-2">
          <button
            v-for="item in methods"
            :key="item.id"
            class="flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition disabled:opacity-40"
            :class="payMethod === item.id ? 'border-[var(--pv-accent)] bg-[var(--pv-accent)]/10' : 'border-[var(--pv-border)]'"
            :disabled="!item.enabled"
            @click="payMethod = item.id"
          >
            <Icon :name="item.id === 'wechat' ? 'message' : item.id === 'alipay' ? 'card' : 'coin'" :size="18" />
            <span class="flex-1">
              {{ item.name }}
              <span class="ml-2 text-[11px] muted">
                {{ item.id === 'manual' ? '联系管理员确认收款' : item.mode === 'qr' ? '站内扫码' : item.mode === 'page' ? '跳转支付宝页面' : '微信扫码' }}
              </span>
            </span>
            <span v-if="!item.enabled" class="text-[11px] muted">未配置</span>
          </button>
        </div>

        <div v-if="payState?.mode === 'qr'" class="space-y-2 text-center">
          <img :src="payState.qrUrl" class="mx-auto h-48 w-48 rounded-xl bg-white p-2" alt="支付二维码" />
          <p class="text-xs muted">用手机扫码支付，页面会自动刷新（状态：{{ payState.status === 'paid' ? '已支付' : '等待支付' }}）</p>
        </div>
        <div v-else-if="payState?.mode === 'page'" class="space-y-2 text-center text-xs muted">
          <p>已打开支付宝收银台，如果没弹出请点下面的链接：</p>
          <a :href="payState.payUrl" target="_blank" class="link break-all">去支付宝支付</a>
          <p>支付完成后本页会自动更新（状态：{{ payState.status === 'paid' ? '已支付' : '等待支付' }}）</p>
        </div>
        <p v-else-if="payState?.mode === 'manual'" class="rounded-xl bg-[var(--pv-surface-2)] p-3 text-xs muted">
          {{ payState.message || '下单后请联系管理员并提供订单号，管理员确认收款后权益会自动到账。' }}
        </p>

        <div class="flex justify-end gap-2 pt-1">
          <button class="btn-ghost" @click="closeCheckout">关闭</button>
          <button v-if="!payState" class="btn-primary" :disabled="busy" @click="confirmPay">
            {{ busy ? '下单中…' : '确认支付' }}
          </button>
        </div>
      </div>
    </div>
</template>
