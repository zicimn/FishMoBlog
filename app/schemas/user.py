from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


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


def to_user_info(user) -> dict:
    # is_admin 是加法式新增（不改动既有键）：前端据此判断是否渲染后台入口。
    # DB 里可能是 NULL，统一归一成 bool。
    return {
        "email": user.email,
        "username": user.username,
        "is_admin": bool(user.is_admin),
    }