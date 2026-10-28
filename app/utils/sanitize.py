"""评论内容的 XSS 清洗。

只依赖 nh3（Rust 版 ammonia 的 Python 绑定）。一律走**显式白名单**，
绝不用 nh3 的默认标签集合（nh3.ALLOWED_TAGS 比这里宽得多）。
"""

import nh3

# 只放行评论正文真正需要的排版标签。
# 刻意不放行 img：评论里的图片会加载任意外部资源（追踪像素、混合内容），
# 收益低而攻击面大；若日后确实要支持站内图床，应做域白名单而不是放开 img。
_ALLOWED_TAGS = {
    "p",
    "br",
    "a",
    "strong",
    "b",
    "em",
    "i",
    "code",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
}

# 属性按标签白名单：只有链接允许带 href/title，其余标签的属性一律剥离。
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
}

# 协议白名单：挡掉 javascript: / data: / vbscript: 等危险 scheme。
# 注意 href="javascript:alert(1)" 会被整条剥离（而不是转义保留）。
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_html(html: str) -> str:
    """把用户提交的 HTML 清洗成安全子集。

    Args:
        html: 原始 HTML（可能夹带脚本 / 事件属性 / 危险协议链接）。

    Returns:
        仅含白名单标签、属性、协议的 HTML 字符串；危险内容被**剥离**，
        而不是转义后原样展示。清洗后可能为空串（如内容只有 ``<script>``），
        调用方需自行处理该情况。
    """
    return nh3.clean(
        html or "",
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        # a 标签统一补 rel="noopener noreferrer"，防 tab-nabbing / referrer 泄露
        link_rel="noopener noreferrer",
        # 注释也一并剥离，避免条件注释之类的老套路
        strip_comments=True,
    )