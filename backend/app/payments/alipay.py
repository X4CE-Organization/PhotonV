"""支付宝：电脑网站支付（跳转）与当面付（站内二维码），含 RSA2 签名与回调验签。"""
from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .. import settings_store as site


def enabled() -> bool:
    return site.get_bool("alipay_enabled", False) and site.get_bool("pay_enabled", False)


def configured() -> bool:
    return bool(
        enabled()
        and site.get_str("alipay_app_id").strip()
        and site.get_str("alipay_private_key").strip()
    )


def mode() -> str:
    value = site.get_str("alipay_mode", "page")
    return value if value in {"page", "qr"} else "page"


def _pem(text: str, kind: str) -> bytes:
    raw = (text or "").strip()
    if "BEGIN" in raw:
        return raw.encode()
    header = "PRIVATE KEY" if kind == "private" else "PUBLIC KEY"
    body = "\n".join(raw[index : index + 64] for index in range(0, len(raw), 64))
    return f"-----BEGIN {header}-----\n{body}\n-----END {header}-----\n".encode()


def _private_key():
    key = serialization.load_pem_private_key(_pem(site.get_str("alipay_private_key"), "private"), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("支付宝应用私钥不是 RSA 私钥")
    return key


def _public_key():
    return serialization.load_pem_public_key(_pem(site.get_str("alipay_public_key"), "public"))


def _hash_algorithm() -> hashes.HashAlgorithm:
    is_rsa2 = site.get_str("alipay_sign_type", "RSA2").upper() == "RSA2"
    return hashes.SHA256() if is_rsa2 else hashes.SHA1()


def _sign_content(params: dict) -> str:
    return "&".join(f"{key}={params[key]}" for key in sorted(params) if params[key] not in (None, ""))


def sign(params: dict) -> str:
    content = _sign_content({key: value for key, value in params.items() if key not in {"sign", "sign_type"}})
    signature = _private_key().sign(content.encode("utf-8"), padding.PKCS1v15(), _hash_algorithm())
    return base64.b64encode(signature).decode()


def verify_notify(params: dict) -> bool:
    """用支付宝公钥校验异步通知签名。"""
    signature = params.get("sign")
    if not signature:
        return False
    content = _sign_content({key: value for key, value in params.items() if key not in {"sign", "sign_type"}})
    try:
        _public_key().verify(
            base64.b64decode(signature), content.encode("utf-8"), padding.PKCS1v15(), _hash_algorithm()
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def _common_params(method: str, biz_content: dict) -> dict:
    from . import notify_url

    return {
        "app_id": site.get_str("alipay_app_id"),
        "method": method,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": site.get_str("alipay_sign_type", "RSA2"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": notify_url("alipay"),
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }


def page_pay(out_trade_no: str, amount_yuan: str, subject: str) -> str:
    """电脑网站支付：返回可直接跳转的收银台地址。"""
    from . import return_url

    params = _common_params(
        "alipay.trade.page.pay",
        {
            "out_trade_no": out_trade_no,
            "total_amount": amount_yuan,
            "subject": subject[:120],
            "product_code": "FAST_INSTANT_TRADE_PAY",
        },
    )
    params["return_url"] = return_url()
    params["sign"] = sign(params)
    gateway = site.get_str("alipay_gateway", "https://openapi.alipay.com/gateway.do").strip()
    return f"{gateway}?{urllib.parse.urlencode(params)}"


def _call(params: dict) -> dict:
    gateway = site.get_str("alipay_gateway", "https://openapi.alipay.com/gateway.do").strip()
    request = urllib.request.Request(
        gateway,
        data=urllib.parse.urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", "ignore"))


def precreate(out_trade_no: str, amount_yuan: str, subject: str) -> dict:
    """当面付：返回二维码内容（前端渲染成二维码图片）。"""
    params = _common_params(
        "alipay.trade.precreate",
        {"out_trade_no": out_trade_no, "total_amount": amount_yuan, "subject": subject[:120]},
    )
    params["sign"] = sign(params)
    payload = _call(params)
    body = payload.get("alipay_trade_precreate_response", {})
    if body.get("code") != "10000":
        return {"ok": False, "error": body.get("sub_msg") or body.get("msg") or str(payload)[:200]}
    return {"ok": True, "qrCode": body.get("qr_code", "")}


def query(out_trade_no: str) -> dict:
    """主动查询订单（用于支付后轮询确认）。"""
    params = _common_params("alipay.trade.query", {"out_trade_no": out_trade_no})
    params["sign"] = sign(params)
    try:
        payload = _call(params)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    body = payload.get("alipay_trade_query_response", {})
    return {
        "ok": body.get("code") == "10000",
        "state": body.get("trade_status", ""),
        "tradeNo": body.get("trade_no", ""),
        "amount": body.get("total_amount", ""),
        "raw": body,
    }
