/**
 * 极简 Markdown 渲染器，只覆盖 `content/about.md` 用到的语法。
 *
 * 为什么不用 marked / markdown-it：这里只需要标题、段落、列表、引用、
 * 代码块与几种行内标记，为一段静态文案引一个解析库不划算（项目也没装）。
 *
 * 安全取向：输入先做 HTML 转义，再拼接标签——也就是说 Markdown 里写不了原始
 * HTML，链接协议也做了白名单。内容来自仓库内文件，本身可信，但这里仍按
 * 「输出即 HTML」的边界处理。
 *
 * 支持：
 *   - 块级：`#`~`####` 标题、段落、`-`/`*` 无序列表、`1.` 有序列表、
 *           `>` 引用、``` 围栏代码块、`---` 分隔线
 *   - 行内：**粗体**、`代码`、[链接](url)
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderInline(text: string): string {
  // 先按行内代码切分：代码块里的 ** / [] 不应该被继续解析
  return text
    .split(/(`[^`]+`)/g)
    .map((part) => {
      if (part.length > 2 && part.startsWith('`') && part.endsWith('`')) {
        return `<code>${escapeHtml(part.slice(1, -1))}</code>`
      }

      let html = escapeHtml(part)
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_match, label: string, href: string) => {
        const safeHref = /^(https?:\/\/|mailto:|\/|#)/i.test(href) ? href : '#'
        const external = /^https?:\/\//i.test(safeHref)
        const attrs = external ? ' target="_blank" rel="noopener noreferrer"' : ''
        return `<a href="${safeHref}"${attrs}>${label}</a>`
      })
      return html
    })
    .join('')
}

export function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n?/g, '\n').split('\n')
  const out: string[] = []

  let paragraph: string[] = []
  let list: string[] = []
  let ordered = false
  let quote: string[] = []

  function flushParagraph() {
    if (!paragraph.length) return
    out.push(`<p>${paragraph.map(renderInline).join('\n')}</p>`)
    paragraph = []
  }

  function flushList() {
    if (!list.length) return
    const tag = ordered ? 'ol' : 'ul'
    out.push(`<${tag}>${list.map((item) => `<li>${renderInline(item)}</li>`).join('')}</${tag}>`)
    list = []
  }

  function flushQuote() {
    if (!quote.length) return
    out.push(`<blockquote><p>${quote.map(renderInline).join(' ')}</p></blockquote>`)
    quote = []
  }

  function flushAll() {
    flushParagraph()
    flushList()
    flushQuote()
  }

  for (let i = 0; i < lines.length; i += 1) {
    const line = (lines[i] ?? '').trim()

    // 围栏代码块：内容原样保留，只做转义
    if (line.startsWith('```')) {
      flushAll()
      const lang = line.slice(3).trim()
      const code: string[] = []
      i += 1
      while (i < lines.length && !(lines[i] ?? '').trim().startsWith('```')) {
        code.push(lines[i] ?? '')
        i += 1
      }
      const cls = lang ? ` class="language-${escapeHtml(lang)}"` : ''
      out.push(`<pre><code${cls}>${escapeHtml(code.join('\n'))}</code></pre>`)
      continue
    }

    if (!line) {
      flushAll()
      continue
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(line)
    if (heading) {
      flushAll()
      const level = heading[1]!.length
      out.push(`<h${level}>${renderInline(heading[2] ?? '')}</h${level}>`)
      continue
    }

    if (/^(-{3,}|\*{3,})$/.test(line)) {
      flushAll()
      out.push('<hr>')
      continue
    }

    if (line.startsWith('> ')) {
      flushParagraph()
      flushList()
      quote.push(line.slice(2))
      continue
    }

    const unordered = /^[-*]\s+(.*)$/.exec(line)
    const orderedItem = /^\d+\.\s+(.*)$/.exec(line)
    if (unordered || orderedItem) {
      flushParagraph()
      flushQuote()
      const isOrdered = Boolean(orderedItem)
      if (list.length && ordered !== isOrdered) flushList()
      ordered = isOrdered
      list.push((unordered?.[1] ?? orderedItem?.[1]) ?? '')
      continue
    }

    flushList()
    flushQuote()
    paragraph.push(line)
  }

  flushAll()
  return out.join('\n')
}