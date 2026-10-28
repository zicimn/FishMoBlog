// 极简全局提示。用 useState 而不是 Pinia：它本来就是跨组件共享的一次性 UI 状态，
// 不需要 devtools 追踪，也不需要持久化。
type ToastKind = 'ok' | 'err'
type Toast = { id: number; text: string; kind: ToastKind }

export function useToast() {
  const items = useState<Toast[]>('app-toasts', () => [])

  function push(text: string, kind: ToastKind) {
    const id = Date.now() + Math.random()
    items.value = [...items.value, { id, text, kind }]
    setTimeout(() => {
      items.value = items.value.filter((t) => t.id !== id)
    }, 3600)
  }

  return {
    items,
    ok: (text: string) => push(text, 'ok'),
    err: (text: string) => push(text, 'err'),
    dismiss: (id: number) => {
      items.value = items.value.filter((t) => t.id !== id)
    },
  }
}