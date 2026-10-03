"""短信验证码：阿里云 / 腾讯云 / 自定义 HTTP 网关 / 开发模式。

只用标准库实现各家的签名算法，没有额外依赖；未配置或调用失败时
自动降级为「开发模式」——验证码写进站内信，方便本地调试。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, settings_store as site


def enabled() -> bool:
    return site.get_bool("sms_enabled", False) and provider() != "dev"


def provider() -> str:
    return site.get_str("sms_provider", "dev") or "dev"


def normalize(phone: str) -> str:
    value = str(phone or "").strip().replace(" ", "").replace("-", "")
    if value.startswith("00"):
        value = "+" + value[2:]
    if not value.startswith("+") and len(value) == 11 and value.startswith("1"):
        value = "+86" + value
    return value


def valid(phone: str) -> bool:
    value = normalize(phone)
    digits = value.lstrip("+")
    return value.startswith("+") and digits.isdigit() and 6 <= len(digits) <= 15


def masked(phone: Optional[str]) -> str:
    if not phone:
        return ""
    if not site.get_bool("phone_mask", True):
        return phone
    digits = phone.lstrip("+")
    if len(digits) < 7:
        return phone
    prefix = phone[: len(phone) - len(digits) + 3]
    return f"{prefix}****{digits[-4:]}"


def _code() -> str:
    length = max(4, min(8, site.get_int("sms_code_length", 6)))
    return "".join(random.choice("0123456789") for _ in range(length))


# --------------------------------------------------------------- 发送实现


def _aliyun_send(phone: str, code: str) -> dict:
    key_id = site.get_str("sms_aliyun_key_id")
    key_secret = site.get_str("sms_aliyun_key_secret")
    if not key_id or not key_secret:
        return {"ok": False, "error": "未配置阿里云 AccessKey"}
    params = {
        "AccessKeyId": key_id,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone.lstrip("+"),
        "RegionId": "cn-hangzhou",
        "SignName": site.get_str("sms_sign_name"),
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "TemplateCode": site.get_str("sms_template_code"),
        "TemplateParam": json.dumps({"code": code}, ensure_ascii=False),
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    query = "&".join(
        f"{urllib.parse.quote(key, safe='')}={urllib.parse.quote(str(value), safe='')}"
        for key, value in sorted(params.items())
    )
    string_to_sign = "POST&%2F&" + urllib.parse.quote(query, safe="")
    signature = base64.b64encode(
        hmac.new((key_secret + "&").encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    body = f"{query}&Signature={urllib.parse.quote(signature, safe='')}".encode()
    request = urllib.request.Request(
        "https://dysmsapi.aliyuncs.com/",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8", "ignore"))
    if payload.get("Code") == "OK":
        return {"ok": True}
    return {"ok": False, "error": payload.get("Message") or str(payload)[:200]}


def _tencent_send(phone: str, code: str) -> dict:
    secret_id = site.get_str("sms_tencent_secret_id")
    secret_key = site.get_str("sms_tencent_secret_key")
    app_id = site.get_str("sms_tencent_sdk_app_id")
    if not secret_id or not secret_key or not app_id:
        return {"ok": False, "error": "未配置腾讯云 SecretId / SecretKey / SmsSdkAppId"}

    host = "sms.tencentcloudapi.com"
    service = "sms"
    payload = json.dumps(
        {
            "PhoneNumberSet": [phone],
            "SmsSdkAppId": app_id,
            "SignName": site.get_str("sms_sign_name"),
            "TemplateId": site.get_str("sms_template_code"),
            "TemplateParamSet": [code],
        },
        separators=(",", ":"),
    )
    timestamp = int(datetime.utcnow().timestamp())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
    hashed_payload = hashlib.sha256(payload.encode()).hexdigest()
    canonical = "\n".join(
        [
            "POST",
            "/",
            "",
            f"content-type:application/json; charset=utf-8\nhost:{host}\n",
            "content-type;host",
            hashed_payload,
        ]
    )
    string_to_sign = "\n".join(
        [
            "TC3-HMAC-SHA256",
            str(timestamp),
            f"{date}/{service}/tc3_request",
            hashlib.sha256(canonical.encode()).hexdigest(),
        ]
    )

    def _sign(key: bytes, message: str) -> bytes:
        return hmac.new(key, message.encode(), hashlib.sha256).digest()

    secret_date = _sign(("TC3" + secret_key).encode(), date)
    secret_service = _sign(secret_date, service)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    authorization = (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{date}/{service}/tc3_request, "
        f"SignedHeaders=content-type;host, Signature={signature}"
    )
    request = urllib.request.Request(
        f"https://{host}/",
        data=payload.encode(),
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": "SendSms",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": "2021-01-11",
            "X-TC-Region": "ap-guangzhou",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8", "ignore"))
    detail = result.get("Response", {})
    if detail.get("Error"):
        return {"ok": False, "error": detail["Error"].get("Message") or str(detail)[:200]}
    statuses = detail.get("SendStatusSet") or []
    if statuses and statuses[0].get("Code") == "Ok":
        return {"ok": True}
    return {"ok": False, "error": str(statuses)[:200]}


def _custom_send(phone: str, code: str) -> dict:
    url = site.get_str("sms_custom_url").strip()
    if not url:
        return {"ok": False, "error": "未配置自定义短信网关地址"}
    template = site.get_str("sms_custom_body") or '{"phone":"{phone}","code":"{code}"}'
    body = (
        template.replace("{phone}", phone)
        .replace("{code}", code)
        .replace("{sign}", site.get_str("sms_sign_name"))
        .replace("{template}", site.get_str("sms_template_code"))
    ).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        text = response.read().decode("utf-8", "ignore")
    marker = site.get_str("sms_custom_success_key", '"ok":true')
    if marker and marker not in text:
        return {"ok": False, "error": text[:200] or "网关未返回成功标识"}
    return {"ok": True}


def send_sms(phone: str, code: str) -> dict:
    """按配置发送短信；失败不抛异常，返回 {ok, error}。"""
    name = provider()
    if name == "dev" or not site.get_bool("sms_enabled", False):
        return {"ok": False, "dev": True, "error": "短信服务未启用（开发模式）"}
    try:
        if name == "aliyun":
            return _aliyun_send(phone, code)
        if name == "tencent":
            return _tencent_send(phone, code)
        if name == "custom":
            return _custom_send(phone, code)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": f"未知的短信服务商：{name}"}


# --------------------------------------------------------------- 验证码


def issue(db: Session, phone: str, purpose: str, user_id: Optional[int] = None) -> str:
    code = _code()
    ttl = site.get_int("sms_code_ttl_minutes", 10)
    db.query(models.SmsCode).filter(
        models.SmsCode.phone == phone,
        models.SmsCode.purpose == purpose,
        models.SmsCode.used.is_(False),
    ).update({"used": True})
    db.add(
        models.SmsCode(
            phone=phone,
            code=code,
            purpose=purpose,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl),
        )
    )
    db.commit()
    return code


def consume(db: Session, phone: str, purpose: str, code: str) -> bool:
    row = db.scalar(
        select(models.SmsCode)
        .where(
            models.SmsCode.phone == phone,
            models.SmsCode.purpose == purpose,
            models.SmsCode.used.is_(False),
            models.SmsCode.expires_at > datetime.utcnow(),
        )
        .order_by(models.SmsCode.id.desc())
    )
    if not row or row.attempts >= 5:
        return False
    if row.code != str(code).strip():
        row.attempts += 1
        db.commit()
        return False
    row.used = True
    db.commit()
    return True


def recent(db: Session, phone: str, seconds: int, purpose: Optional[str] = None) -> int:
    """同一手机号在该用途下的发送次数（用途之间互不影响）。"""
    query = select(func.count(models.SmsCode.id)).where(
        models.SmsCode.phone == phone,
        models.SmsCode.created_at >= datetime.utcnow() - timedelta(seconds=seconds),
    )
    if purpose:
        query = query.where(models.SmsCode.purpose == purpose)
    return int(db.scalar(query) or 0)


def today_count(db: Session, phone: str) -> int:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(
        db.scalar(
            select(func.count(models.SmsCode.id)).where(
                models.SmsCode.phone == phone, models.SmsCode.created_at >= today
            )
        )
        or 0
    )


def by_phone(db: Session, phone: str) -> Optional[models.User]:
    return db.scalar(select(models.User).where(models.User.phone == phone))
