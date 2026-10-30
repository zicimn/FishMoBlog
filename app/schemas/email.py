"""邮箱验证码接口的入参模型。

独立的 ``SendCodeRequest`` 而不是复用 ``RegisterRequest``：发送验证码阶段只应
接收邮箱，多一个字段就多一处「用户能在拿到验证码之前提交密码」的攻击面
（密码会被 argon2 哈希后…… 其实不会落库，但完全没有必要接收）。
"""

from pydantic import BaseModel, EmailStr, Field


class SendCodeRequest(BaseModel):
    # 与 User.email 的列宽保持一致（String(100)）：先由 Pydantic 挡住超长输入，
    # 避免它一路流到 Redis key 与邮件头里。
    email: EmailStr = Field(max_length=100)
    # 本端点只发注册码。注销码走登录态的 POST /user/delete-code，避免公开
    # 接口被用来向任意邮箱投递「注销账号」警告邮件。