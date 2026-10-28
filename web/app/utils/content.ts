export interface TocItem {
  id: string
  level: number
  text: string
}

const ENTITIES: Record<string, string> = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&nbsp;': ' ',
}

// 只用于统计/目录文字，不追求完整 HTML 解析
export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (entity) => ENTITIES[entity] ?? entity)
    .replace(/\s+/g, ' ')
    .trim()
}

// 给正文标题补锚点 id 并抽出目录。参考 Mizuki / RyuChan 的侧边目录：
// 后端存的 HTML 没有 id，只能渲染前统一注入，目录和滚动高亮才能对上。
export function buildToc(html: string): { html: string; toc: TocItem[] } {
  const toc: TocItem[] = []
  let index = 0

  const withIds = html.replace(
    /<h([1-4])([^>]*)>([\s\S]*?)<\/h\1>/gi,
    (match: string, level: string, attrs: string, inner: string) => {
      const text = stripHtml(inner)
      if (!text) return match
      const id = `h-${index++}`
      toc.push({ id, level: Number(level), text })
      const cleanAttrs = attrs.replace(/\sid=(["']).*?\1/i, '')
      return `<h${level}${cleanAttrs} id="${id}">${inner}</h${level}>`
    },
  )

  return { html: withIds, toc }
}