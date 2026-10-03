"""微信支付 v3：Native 扫码下单、回调解密（AES-256-GCM）与主动查单。"""
from __future__ import annotations

from typing import Optional

import base64
import json
import time
import urllib.parse
import urllib.request
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .. import settings_store as site

API_BASE = "https://api.mch.weixin.qq.com"


def enabled() -> bool:
    return site.get_bool("wechat_enabled", False) and site.get_bool("pay_enabled", False)


def configured() -> bool:
    return bool(
        enabled()
        and site.get_str("wechat_mchid").strip()
        and site.get_str("wechat_serial_no").strip()
        and site.get_str("wechat_private_key").strip()
        and site.get_str("wechat_api_v3_key").strip()
    )


def _pem(text: str) -> bytes:
    raw = (text or "").strip()
    if "BEGIN" in raw:
        return raw.encode()
    body = "\n".join(raw[index : index + 64] for index in range(0, len(raw), 64))
    return f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY-----\n".encode()


def _private_key():
    key = serialization.load_pem_private_key(_pem(site.get_str("wechat_private_key")), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("微信支付商户私钥不是 RSA 私钥")
    return key


def _authorization(method: str, url_path: str, body: str) -> str:
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = base64.b64encode(
        _private_key().sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    return (
        "WECHATPAY2-SHA256-RSA2048 "
        f'mchid="{site.get_str("wechat_mchid")}",'
        f'nonce_str="{nonce}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{site.get_str("wechat_serial_no")}"'
    )


def _request(method: str, url_path: str, payload: Optional[dict] = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) if payload is not None else ""
    if not url_path.startswith("/"):
        url_path = "/" + url_path
    request = urllib.request.Request(
        f"{API_BASE}{url_path}",
        data=body.encode() if body else None,
        method=method,
        headers={
            "Authorization": _authorization(method, url_path, body),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PhotonV/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode("utf-8", "ignore")
    return json.loads(text) if text else {}


def native_order(out_trade_no: str, amount_cents: int, subject: str, notify_url: str) -> dict:
    """Native 下单：返回二维码链接（code_url）。"""
    endpoint = site.get_str("wechat_native_url", f"{API_BASE}/v3/pay/transactions/native").strip()
    path = endpoint.replace(API_BASE, "") or "/v3/pay/transactions/native"
    payload = {
        "appid": site.get_str("wechat_appid"),
        "mchid": site.get_str("wechat_mchid"),
        "description": subject[:120],
        "out_trade_no": out_trade_no,
        "notify_url": notify_url,
        "amount": {"total": int(amount_cents), "currency": "CNY"},
    }
    try:
        result = _request("POST", path, payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    if result.get("code_url"):
        return {"ok": True, "codeUrl": result["code_url"]}
    return {"ok": False, "error": result.get("message") or str(result)[:200]}


def query(out_trade_no: str) -> dict:
    path = (
        f"/v3/pay/transactions/out-trade-no/{urllib.parse.quote(out_trade_no)}"
        f"?mchid={site.get_str('wechat_mchid')}"
    )
    try:
        result = _request("GET", path)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    return {
        "ok": True,
        "state": result.get("trade_state", ""),
        "tradeNo": result.get("transaction_id", ""),
        "amount": (result.get("amount") or {}).get("total", 0),
        "raw": result,
    }


def decrypt_resource(resource: dict) -> dict:
    """解密回调里的 resource（AES-256-GCM，密钥是 APIv3 密钥）。"""
    key = site.get_str("wechat_api_v3_key").encode()
    if len(key) != 32:
        raise ValueError("微信支付 APIv3 密钥必须是 32 位")
    aesgcm = AESGCM(key)
    data = base64.b64decode(resource["ciphertext"])
    nonce = resource["nonce"].encode()
    associated = (resource.get("associated_data") or "").encode()
    plain = aesgcm.decrypt(nonce, data, associated)
    return json.loads(plain.decode("utf-8"))
