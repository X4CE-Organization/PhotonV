<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, query } from '../../api';
import { toast } from '../../composables/toast';
import { useAppStore } from '../../store';
import { formatTime, initials } from '../../utils';
import PaginationBar from '../../components/PaginationBar.vue';
import Icon from '../../components/Icon.vue';

const store = useAppStore();
const items = ref<any[]>([]);
const stats = ref<any>({});
const plans = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(30);
const status = ref('pending');
const type = ref('');
const loading = ref(true);
const handling = ref<any>(null);
const note = ref('');
const editingPlan = ref<any>(null);
const planForm = ref({ name: '', days: 30, priceYuan: 15, description: '', badge: '大会员', sort: 0, isActive: true });

async function load() {
  loading.value = true;
  try {
    const data = await api.get<any>(`/api/admin/orders${query({ status: status.value, type: type.value, page: page.value })}`);
    items.value = data.items || [];
    total.value = data.total || 0;
    size.value = data.size || 30;
    stats.value = data.stats || {};
    if (store.isAdmin) {
      const planData = await api.get<any>('/api/admin/plans');
      plans.value = planData.items || [];
    }
  } finally {
    loading.value = false;
  }
}

async function review(action: string) {
  try {
    await api.post(`/api/admin/orders/${handling.value.id}/review`, { action, note: note.value });
    toast.success('已处理');
    handling.value = null;
    note.value = '';
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '操作失败');
  }
}

function openPlan(plan?: any) {
  editingPlan.value = plan || { id: 0 };
  planForm.value = plan
    ? { name: plan.name, days: plan.days, priceYuan: plan.priceYuan, description: plan.description, badge: plan.badge, sort: plan.sort, isActive: plan.isActive }
    : { name: '', days: 30, priceYuan: 15, description: '', badge: '大会员', sort: plans.value.length, isActive: true };
}

async function savePlan() {
  try {
    if (editingPlan.value.id) await api.put(`/api/admin/plans/${editingPlan.value.id}`, planForm.value);
    else await api.post('/api/admin/plans', planForm.value);
    toast.success('已保存');
    editingPlan.value = null;
    void load();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '保存失败');
  }
}

async function removePlan(plan: any) {
  if (!window.confirm(`确定删除套餐「${plan.name}」吗？`)) return;
  await api.del(`/api/admin/plans/${plan.id}`);
  toast.success('已删除');
  void load();
}

onMounted(load);
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-base font-semibold">订单与会员</h1>
      <span class="text-xs muted">累计收入 ¥{{ ((stats.revenueCents || 0) / 100).toFixed(2) }} · 待处理 {{ stats.pending || 0 }} · 已支付 {{ stats.paid || 0 }}</span>
    </div>

    <div class="surface flex flex-wrap items-center gap-2 p-3">
      <select v-model="status" class="input !w-32" @change="page = 1; load()">
        <option value="pending">待处理</option>
        <option value="paid">已支付</option>
        <option value="cancelled">已取消</option>
        <option value="refunded">已退款</option>
        <option value="">全部</option>
      </select>
      <select v-model="type" class="input !w-32" @change="page = 1; load()">
        <option value="">全部类型</option>
        <option value="membership">会员</option>
        <option value="coins">充值</option>
        <option value="charge">充电</option>
      </select>
      <span class="ml-auto text-xs muted">共 {{ total }} 条</span>
    </div>

    <p v-if="loading" class="py-10 text-center text-sm muted">加载中…</p>
    <div v-else class="surface overflow-x-auto">
      <table class="table-base">
        <thead>
          <tr>
            <th class="w-44">订单号</th><th class="w-32">用户</th><th>内容</th>
            <th class="w-24">金额</th><th class="w-20">硬币</th><th class="w-24">状态</th>
            <th class="w-32">时间</th><th class="w-24">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="font-mono text-xs">{{ item.orderNo }}</td>
            <td class="text-xs">
              <div class="flex items-center gap-1.5">
                <img v-if="item.buyer?.avatar" :src="item.buyer.avatar" class="h-6 w-6 rounded-full object-cover" alt="" />
                <span v-else class="grid h-6 w-6 place-items-center rounded-full bg-[var(--pv-surface-2)] text-[10px] font-bold">
                  {{ initials(item.buyer?.displayName) }}
                </span>
                {{ item.buyer?.displayName }}
              </div>
            </td>
            <td class="text-sm">
              {{ item.title }}
              <div v-if="item.target" class="text-[11px] muted">给 {{ item.target.displayName }} 充电</div>
            </td>
            <td class="text-xs">¥{{ (item.amountCents / 100).toFixed(2) }}</td>
            <td class="text-xs">{{ item.coins || '—' }}</td>
            <td class="text-xs">
              <span :class="item.status === 'paid' ? 'text-emerald-500' : item.status === 'pending' ? 'text-amber-500' : 'muted'">
                {{ item.status === 'paid' ? '已支付' : item.status === 'pending' ? '待处理' : item.status === 'cancelled' ? '已取消' : '已退款' }}
              </span>
            </td>
            <td class="text-xs muted">{{ formatTime(item.createdAt) }}</td>
            <td>
              <button v-if="item.status === 'pending'" class="text-xs text-[var(--pv-accent)] hover:underline" @click="handling = item">处理</button>
              <span v-else class="text-xs muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!items.length" class="p-10 text-center text-sm muted">没有订单</p>
    </div>
    <PaginationBar :page="page" :size="size" :total="total" @change="(value) => { page = value; load(); }" />

    <section v-if="store.isSuperadmin" class="surface p-4">
      <div class="flex items-center justify-between">
        <h2 class="flex items-center gap-2 text-sm font-semibold"><Icon name="crown" :size="16" />会员套餐</h2>
        <button class="btn-ghost text-xs" @click="openPlan()">新增套餐</button>
      </div>
      <ul class="mt-3 divide-y divide-[var(--pv-border)]">
        <li v-for="plan in plans" :key="plan.id" class="flex flex-wrap items-center gap-3 py-2.5 text-sm">
          <span class="font-medium">{{ plan.name }}</span>
          <span class="chip">{{ plan.days }} 天</span>
          <span class="text-[var(--pv-accent)]">¥{{ plan.priceYuan }}</span>
          <span class="text-xs muted">{{ plan.description }}</span>
          <span v-if="!plan.isActive" class="text-[11px] text-amber-500">已停用</span>
          <span class="ml-auto flex gap-2 text-xs">
            <button class="text-[var(--pv-accent)] hover:underline" @click="openPlan(plan)">编辑</button>
            <button class="text-rose-500 hover:underline" @click="removePlan(plan)">删除</button>
          </span>
        </li>
        <li v-if="!plans.length" class="py-4 text-xs muted">还没有套餐</li>
      </ul>
    </section>

    <div v-if="handling" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="handling = null">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h2 class="text-sm font-semibold">处理订单 {{ handling.orderNo }}</h2>
        <p class="text-xs muted">{{ handling.title }} · ¥{{ (handling.amountCents / 100).toFixed(2) }}</p>
        <textarea v-model="note" class="input min-h-[80px]" placeholder="处理备注（会通知用户）"></textarea>
        <div class="flex flex-wrap justify-end gap-2">
          <button class="btn-ghost text-xs" @click="review('reject')">驳回并退款</button>
          <button class="btn-ghost text-xs" @click="review('refund')">标记退款</button>
          <button class="btn-primary text-xs" @click="review('approve')">确认收款</button>
        </div>
      </div>
    </div>

    <div v-if="editingPlan" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="editingPlan = null">
      <div class="w-full max-w-md space-y-3 rounded-2xl border border-[var(--pv-border)] bg-[var(--pv-surface)] p-5">
        <h2 class="text-sm font-semibold">{{ editingPlan.id ? '编辑套餐' : '新增套餐' }}</h2>
        <div><label class="label">名称</label><input v-model="planForm.name" class="input" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">天数</label><input v-model.number="planForm.days" type="number" class="input" /></div>
          <div><label class="label">价格（元）</label><input v-model.number="planForm.priceYuan" type="number" class="input" /></div>
        </div>
        <div><label class="label">描述</label><input v-model="planForm.description" class="input" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">标识文字</label><input v-model="planForm.badge" class="input" /></div>
          <div><label class="label">排序</label><input v-model.number="planForm.sort" type="number" class="input" /></div>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="planForm.isActive" type="checkbox" />启用</label>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editingPlan = null">取消</button>
          <button class="btn-primary" @click="savePlan">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
