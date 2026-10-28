import json
from typing import Optional, Any
import redis.asyncio as redis


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    password=None,      # Redis 密码
    decode_responses=True,          # 自动解码为字符串
    encoding="utf-8",              # 编码格式
    max_connections=20,             # 连接池最大连接数
    socket_connect_timeout=5,       # 连接超时（秒）
    socket_timeout=5,               # 操作超时（秒）
    health_check_interval=30        # 健康检查间隔
)


SEARCH_VERSION_KEY = "search_version"


async def get_search_version(name: str = SEARCH_VERSION_KEY):
    v = await redis_client.get(name)
    return int(v or 0)


async def update_version(name: str = SEARCH_VERSION_KEY):
    await redis_client.incr(name)


def get_cache_key(prefix: str, *args, version: int = None, **kwargs) -> str:
    key_parts = [prefix]

    if version is not None:
        key_parts.append(f"v{version}")

    key_parts.extend([str(arg) for arg in args])
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None])
    return ":".join(key_parts)


async def get_from_cache(key: str) -> Optional[Any]:
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_to_cache(key: str, value: Any, expire: int = 300) -> None:
    await redis_client.setex(key, expire, json.dumps(value, default=str))


async def delete_cache(key: str) -> None:
    await redis_client.delete(key)


async def delete_cache_pattern(pattern: str) -> None:
    async for key in redis_client.scan_iter(match=pattern):
        await redis_client.delete(key)


RATE_LIMIT_PREFIX = "rl:"
TOKEN_BLACKLIST_PREFIX = "jwt:blacklist:"


# INCR + 首次设 TTL 必须原子。用 Lua 而不是 `EXPIRE key ttl NX`：后者是
# Redis 7.0 才有的语法，本机 Windows 服务的 redis-server 是 3.0.504，会直接回
# "wrong number of arguments for 'expire'"，而所有调用方都把 Redis 异常当作
# 「失败开放」——限流会静默消失。Lua 在 3.0+ 都可用，语义与原实现完全一致：
# TTL 只在计数第一次创建时设置，后续请求不会把窗口往后推。
_RATE_LIMIT_SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return n
"""


async def rate_limit(key: str, max_attempts: int = 10, window_seconds: int = 300) -> bool:
    """固定窗口限流。返回 True 表示放行，False 表示已达上限。

    窗口 TTL 只在计数第一次创建时设置，否则每次请求都会把窗口往后推，
    限流永远不会生效。
    """
    redis_key = f"{RATE_LIMIT_PREFIX}{key}"
    count = await redis_client.eval(
        _RATE_LIMIT_SCRIPT, 1, redis_key, int(window_seconds)
    )
    return int(count) <= max_attempts


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """把已登出的令牌 jti 写入黑名单，TTL 与其剩余有效期一致，到期自动清理。"""
    if ttl_seconds > 0:
        await redis_client.setex(f"{TOKEN_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    return bool(await redis_client.exists(f"{TOKEN_BLACKLIST_PREFIX}{jti}"))
