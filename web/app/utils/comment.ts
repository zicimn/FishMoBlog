// 评论入参：后端 content 按 HTML 存（nh3 白名单消毒），而前台评论框是纯文本。
// 提交前先把用户输入转义、再把换行换成 <br>，而不是把原始文本当 HTML 发过去
// 指望后端白名单兜底——那样 "<script>" 会成为真正的标签，消毒一旦有缺口就是 XSS。
const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
}

// 与后端 CommentCreateRequest.content max_length=2000 对齐
export const COMMENT_MAX_LENGTH = 2000

/** 纯文本 → 后端可存的 HTML 片段。<br> 在 nh3 白名单里，换行才不会丢。 */
export function commentTextToHtml(text: string): string {
  return text
    // 先统一换行：Windows 的 \r\n 与老 Mac 的 \r 都归一成 \n，否则会出现双倍空行
    .replace(/\r\n?/g, '\n')
    .trim()
    .replace(/[&<>]/g, (ch) => ESCAPES[ch] ?? ch)
    .replace(/\n/g, '<br>')
}