import logging
from typing import Optional
logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500

    def __init__(self, msg: str, *, log: bool = True):
        self.msg = msg
        super().__init__(msg)

        if log:
            logger.warning("%s: %s", self.__class__.__name__, msg)


class NotFound(AppError):
    status_code = 404


class BadRequest(AppError):
    """请求参数或业务前置条件不通过（400）。

    验证码错误 / 过期用它，而不是复用 PwdError(401)：前端对 401 的处理是
    「令牌失效，清登录态并跳登录页」，但填错一个验证码不该把已登录用户踢出去。
    也不该用 500——那是服务端故障，重试同样的请求永远不会成功。
    """
    status_code = 400


class Busy(AppError):
    status_code = 429


class PwdError(AppError):
    status_code = 401


class OpError(AppError):
    status_code = 403

class Conflict(AppError):
    """资源冲突（唯一索引撞车等）。

    单列一类而不是复用 OpError：403 的语义是「没权限」，前端 describeError
    会把它翻成「需要管理员权限」，用在 slug 冲突上会误导用户。
    """
    status_code = 409


def info(
    msg:str = "成功",
    code:int = 200,
    data:Optional[dict] = None
):
    return {
        "msg":msg,
        "code":code,
        "data":data
    }