"""支付渠道：微信支付 v3、支付宝（RSA2）、人工审核。"""
from __future__ import annotations

from . import alipay, wechat


def alipay_ready() -> bool:
    return alipay.configured()


def wechat_ready() -> bool:
    return wechat.configured()


def methods() -> list:
    from .. import settings_store as site

    online = site.get_bool("pay_enabled", False)
    return [
        {"id": "manual", "name": "人工审核 / 转账", "enabled": True, "mode": "manual"},
        {"id": "alipay", "name": "支付宝", "enabled": bool(online and alipay_ready()), "mode": alipay.mode()},
        {"id": "wechat", "name": "微信支付", "enabled": bool(online and wechat_ready()), "mode": "native"},
    ]


def notify_url(kind: str) -> str:
    from .. import settings_store as site

    base = site.get_str("site_url", "").rstrip("/")
    return f"{base}/api/payments/{kind}/notify"


def return_url() -> str:
    from .. import settings_store as site

    configured = site.get_str("pay_return_url", "").strip()
    if configured:
        return configured
    return f"{site.get_str('site_url', '').rstrip('/')}/membership"
