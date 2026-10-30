from typing import Optional
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class LoginRequest(BaseModel):

    email: EmailStr = Field(max_length=100)
    # 登录只做凭据校验，不在此处施加密码强度策略（那会锁死已存在的短密码账号）；
    # 上限用于挡住超长输入拖垮 argon2。强度策略应在注册 / 改密接口里施加。
    password: str = Field(min_length=1, max_length=128)


class ResetPwdRequest(BaseModel):
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=128)
    re_password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    """访客自助注册入参（字段风格对齐 ``ResetPwdRequest``）。

    安全红线：``is_admin`` 与 ``status`` **不在**本模型里，也不允许由请求体传入；
    它们在服务端 Register 中写死（is_admin=0 访客、status=1 正常）。Pydantic 默认
    忽略未声明字段，因此请求体里塞 ``is_admin=1`` 不会产生任何影响。
    """

    email: EmailStr = Field(max_length=100)
    # 邮箱验证码（硬注册）：必须在 Pydantic 层就卡死成 6 位数字。
    # 放到业务层再判断等于让任意长度的字符串一路流过依赖注入、日志与 Redis，
    # 且会让「格式错误」和「验证码错误」混成同一个 400，前端无法区分。
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    re_password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: str) -> str:
        name = (v or "").strip()
        # Field(min_length=2) 校验的是 strip 之前的原始值，这里再确认真实长度
        if len(name) < 2:
            raise ValueError("用户名至少 2 个字符")
        if any(ch.isspace() for ch in name):
            raise ValueError("用户名不能包含空白字符")
        return name

    @model_validator(mode="after")
    def _check_password(self) -> "RegisterRequest":
        if self.password != self.re_password:
            raise ValueError("两次输入的密码不一致")
        # 强度策略（原本注释交代要在这里施加）：至少 8 位（Field 已保证）
        # 且必须同时包含字母和数字，挡住 "12345678" / "password" 这类弱口令。
        if not any(c.isalpha() for c in self.password) or not any(
            c.isdigit() for c in self.password
        ):
            raise ValueError("密码需同时包含字母和数字")
        return self


class UserEditRequest(BaseModel):
    """修改个人资料入参（只含可自助修改的字段）。

    刻意**没有** ``email`` / ``password`` / ``is_admin`` / ``status``：
    邮箱是登录标识与验证码收件地址，改它需要重新验证；密码走独立的重置流程；
    权限与状态只能由后台改动。``extra="forbid"`` 让请求体里塞这些字段直接 422，
    而不是被静默忽略后让人误以为改成功了。

    可空字段（``avatar`` / ``bio``）沿用文章编辑的语义：**键不出现 = 不改，
    键出现且为 null / 空串 = 清空**。判断在 service 层按 ``model_fields_set``
    完成，这里不做「空串转 None」，否则会丢掉「显式清空」这条信息。
    """

    model_config = ConfigDict(extra="forbid")

    # 用户名是必填列：允许不传（不改），但显式传 null 会被下面的校验器拦下。
    username: Optional[str] = Field(default=None, min_length=2, max_length=50)
    # 与 user.avatar 列宽一致；空串 / null 表示清空。
    avatar: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: Optional[str]) -> str:
        # 显式传 null 时也会进到这里：用户名是 NOT NULL 列，不允许清空。
        if v is None:
            raise ValueError("用户名不能为空")
        name = v.strip()
        # Field(min_length=2) 校验的是 strip 之前的原始值，这里再确认真实长度
        if len(name) < 2:
            raise ValueError("用户名至少 2 个字符")
        if any(ch.isspace() for ch in name):
            raise ValueError("用户名不能包含空白字符")
        return name

    @field_validator("avatar")
    @classmethod
    def _clean_avatar(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        url = v.strip()
        if not url:
            return None
        # 头像会直接进 <img src>：只放行 http(s)，挡掉 javascript: / data: 等
        # 非预期 scheme（data: 图片还会绕过上传链路，变成不受控的图床）。
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("头像地址必须是 http(s) 链接")
        return url

    @field_validator("bio")
    @classmethod
    def _clean_bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # bio 按纯文本存储与展示，不做 HTML 消毒（也不接受 HTML 语义）。
        return v.strip() or None


class UserDeleteRequest(BaseModel):
    """注销账号入参：只接收邮箱验证码。

    账号身份由路由层的 ``GetCurrentUser`` 决定，请求体里**不接受** user_id；
    ``extra="forbid"`` 让多传的字段直接 422。验证码格式与注册保持一致，避免
    任意长度字符串一路流到 Redis 与 ``secrets.compare_digest``。
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def to_user_profile(user) -> dict:
    """当前用户自助修改资料后的返回体（含展示字段，绝不含 password_hash）。"""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar": user.avatar or "",
        "bio": user.bio or "",
        "is_admin": bool(user.is_admin),
    }


def to_admin_user(user) -> dict:
    """管理端用户列表项：只挑展示字段，不整行序列化。

    ``status`` 原样返回（0 禁用 / 1 正常），``is_admin`` 归一成 bool；
    ``avatar`` / ``bio`` 的空值统一成空串，前端无需再判 null。
    """
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar": user.avatar or "",
        "bio": user.bio or "",
        "is_admin": bool(user.is_admin),
        "status": user.status,
        "created_at": user.created_at,
    }


def to_user_info(user) -> dict:
    # is_admin 是加法式新增（不改动既有键）：前端据此判断是否渲染后台入口。
    # ID 同样只是加法式新增：前台留言板要判断「这条留言是不是我的」，
    # 只靠用户名不可靠（昵称不保证唯一），用户快照里带上主键最直接。
    # avatar / bio 也是加法式新增：前台「点留言板头像改资料」需要用登录快照
    # 预填当前值，否则用户看不到已有的头像 / 简介。前端只提交真正改动的键，
    # 因此旧快照缺这两个字段也不会误清空；两者本来就是公开展示字段，放进
    # 登录响应不扩大泄露面。
    # DB 里 is_admin 可能是 NULL，统一归一成 bool。
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar": user.avatar or "",
        "bio": user.bio or "",
        "is_admin": bool(user.is_admin),
    }