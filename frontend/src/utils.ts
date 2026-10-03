export function formatNumber(value: number | undefined | null): string {
  const num = Number(value || 0);
  if (num >= 100000000) return `${(num / 100000000).toFixed(1)}亿`;
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  return String(num);
}

export function formatDuration(seconds: number | undefined | null): string {
  const total = Math.max(0, Math.floor(Number(seconds || 0)));
  const hour = Math.floor(total / 3600);
  const minute = Math.floor((total % 3600) / 60);
  const second = total % 60;
  const pad = (value: number) => String(value).padStart(2, '0');
  return hour > 0 ? `${hour}:${pad(minute)}:${pad(second)}` : `${pad(minute)}:${pad(second)}`;
}

export function fromNow(value?: string | null): string {
  if (!value) return '';
  const stamp = new Date(value.replace(' ', 'T') + 'Z').getTime();
  if (Number.isNaN(stamp)) return value;
  const diff = Math.max(0, Date.now() - stamp) / 1000;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} 天前`;
  if (diff < 86400 * 365) return `${Math.floor(diff / 86400 / 30)} 个月前`;
  return `${Math.floor(diff / 86400 / 365)} 年前`;
}

export function formatTime(value?: string | null): string {
  if (!value) return '';
  return value.replace('T', ' ').slice(0, 16);
}

export function formatSize(bytes: number | undefined | null): string {
  const size = Number(bytes || 0);
  if (size >= 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${size} B`;
}

export function initials(name?: string | null): string {
  const text = (name || '?').trim();
  return text.slice(0, 1).toUpperCase();
}

const EMOJI_TOKEN = /\[emoji:([A-Za-z0-9_\-.~:/]+)\]/g;

export function escapeHtml(text: string): string {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * 把普通文本渲染成安全 HTML：转义 + @提及高亮 + 表情图片。
 * 只允许 [emoji:...] 里的地址变成图片，其他标签一律当纯文本处理。
 */
export function renderRich(content: string): string {
  const safe = escapeHtml(content);
  return safe
    .replace(EMOJI_TOKEN, (_match, url: string) => `<img class="pv-emoji" src="${url}" alt="表情" />`)
    .replace(/(^|\s)@([A-Za-z0-9_\u4e00-\u9fa5-]{1,32})/g, '$1<span class="pv-mention">@$2</span>');
}
