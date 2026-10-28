import { describeError } from '~/composables/useApi'

// 图片上传的唯一入口：文章封面与正文插图共用（都要走 admin 分组的 /upload/image）。
// 抽成 composable 而不是各组件各写一遍，是为了让「类型/体积校验、base64 转换、
// 上传中状态、错误文案、失败即放弃」只有一份实现。
//
// 后端链路：base64 → PIL 转 WEBP（限制 25M 像素 / 解压前 5MB）→ Cloudinary，
// 最后把 url 与 public_id 一起回给前端，文章表落库存 url。
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024

export function useImageUpload() {
  const api = useApi()

  const uploading = ref(false)
  const error = ref('')

  function readAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = () => reject(new Error('读取文件失败'))
      reader.readAsDataURL(file)
    })
  }

  /** 上传成功返回 {url, public_id}；失败返回 null，原因写在 error 里。 */
  async function upload(file: File) {
    error.value = ''
    if (!file.type.startsWith('image/')) {
      error.value = '只能上传图片文件'
      return null
    }
    // 前端这道只是为了省一次注定失败的上传：真正的上限在服务端
    //（解压前 5MB + 像素上限，见 app/utils/cloudinary.py）。
    if (file.size > MAX_IMAGE_BYTES) {
      error.value = '图片超过 5MB，请先压缩后再上传'
      return null
    }

    uploading.value = true
    try {
      const image = await readAsDataUrl(file)
      return await api.post<{ url: string; public_id: string }>('/admin/upload/image', { image })
    } catch (err) {
      error.value = describeError(err)
      return null
    } finally {
      uploading.value = false
    }
  }

  /** 尽力删除一张云端图片：失败静默（云端残留不影响用户继续编辑）。 */
  async function remove(publicId: string) {
    if (!publicId) return
    try {
      await api.del('/admin/upload/image', { public_id: publicId })
    } catch {
      // 刻意吞掉：清理失败只意味着 Cloudinary 上多一张孤儿图，
      // 不值得打断用户正在做的事。
    }
  }

  return { uploading, error, upload, remove }
}
