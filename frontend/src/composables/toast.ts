import { ref } from 'vue';

export interface ToastItem {
  id: number;
  message: string;
  kind: 'info' | 'success' | 'error';
}

export const toasts = ref<ToastItem[]>([]);
let seed = 0;

function push(message: string, kind: ToastItem['kind'] = 'info') {
  const id = ++seed;
  toasts.value.push({ id, message, kind });
  setTimeout(() => {
    toasts.value = toasts.value.filter((item) => item.id !== id);
  }, 2600);
}

export const toast = {
  info: (message: string) => push(message, 'info'),
  success: (message: string) => push(message, 'success'),
  error: (message: string) => push(message, 'error'),
};
