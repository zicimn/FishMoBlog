// 后端返回的是 MySQL 的 naive datetime（如 2026-10-27T22:24:38），
// new Date() 会按浏览器本地时区解析，这里只做展示格式化，不做时区换算。
export function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}