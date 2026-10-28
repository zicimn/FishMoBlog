import os
from pathlib import Path

from dotenv import load_dotenv

# 显式指定 .env 位置（app/.env），避免依赖 cwd 或 dotenv 的隐式向上查找
load_dotenv(Path(__file__).parents[1] / ".env")

#MySQL
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")

if not ASYNC_DATABASE_URL:
    raise ValueError("环境变量 ASYNC_DATABASE_URL 未设置，请检查 .env 文件")

#JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise ValueError("SECRET_KEY 未配置,JWT 签名将不可用")

#resend
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY 未配置")

# 发件人地址。**必须是可选项**：新增一个必需变量会让整个 app 在 import 期 raise，
# 而现有 .env 里没有它。缺省值 onboarding@resend.dev 是 Resend 的测试发件人，
# 只能投递到 API key 所属账号的邮箱——真实上线请配置成自己已在 Resend 验证过
# 域名的地址（如 noreply@yourdomain.com），否则验证码发不到用户手里。
RESEND_FROM = os.getenv("RESEND_FROM") or "onboarding@resend.dev"

# Cloudinary
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
    raise ValueError("Cloudinary 配置不完整","图片上传将回退到本地文件系统")




