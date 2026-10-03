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

async function load() {
  loading.value = true;
  try {
    plans.value = await api.get<any>('/api/plans');
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
  busy.value = true;
  try {
    const result = await api.post<any>('/api/orders', { type: 'membership', plan_id: plan.id });
    await api.post(`/api/orders/${result.order.id}/pay`, {});
    toast.success('下单成功，请在订单里查看状态');
    await load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '下单失败');
  } finally {
    busy.value = false;
  }
}

async function recharge() {
  if (!requireLogin()) return;
  busy.value = true;
  try {
    const result = await api.post<any>('/api/orders', { type: 'coins', amount_cents: Math.round(amount.value * 100) });
    await api.post(`/api/orders/${result.order.id}/pay`, {});
    toast.success('充值订单已创建');
    await load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '充值失败');
  } finally {
    busy.value = false;
  }
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

    <div class="grid gap-4 lg:grid-cols-[1fr_340px]">
      <div class="space-y-4">
        <section class="surface p-4">
          <h2 class="text-sm font-semibold">会员套餐</h2>
          <div class="mt-3 grid gap-3 sm:grid-cols-3">
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
</template>
