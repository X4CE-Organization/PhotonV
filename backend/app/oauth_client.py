"""第三方登录（OAuth2 授权码模式）：GitHub / Gitee / Google / 自定义。

提供方信息全部来自系统设置（oauth_<id>_*），只用标准库发请求。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

from . import settings_store as site

PROVIDERS = [
    {
        "id": "github",
        "name": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "color": "#24292f",
    },
    {
        "id": "gitee",
        "name": "Gitee",
        "authorize_url": "https://gitee.com/oauth/authorize",
        "token_url": "https://gitee.com/oauth/token",
        "userinfo_url": "https://gitee.com/api/v5/user",
        "scope": "user_info",
        "color": "#c71d23",
    },
    {
        "id": "google",
        "name": "Google",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
        "color": "#ea4335",
    },
    {
        "id": "custom",
        "name": "自定义 OAuth2",
        "authorize_url": "",
        "token_url": "",
        "userinfo_url": "",
        "scope": "user",
        "color": "#0ea5e9",
    },
]

PRESET_MAP = {item["id"]: item for item in PROVIDERS}


def provider_config(provider_id: str) -> Optional[dict]:
    preset = PRESET_MAP.get(provider_id)
    if not preset:
        return None
    config = dict(preset)
    config.update(
        {
            "client_id": site.get_str(f"oauth_{provider_id}_client_id", ""),
            "client_secret": site.get_str(f"oauth_{provider_id}_client_secret", ""),
            "authorize_url": site.get_str(f"oauth_{provider_id}_authorize_url", preset["authorize_url"]),
            "token_url": site.get_str(f"oauth_{provider_id}_token_url", preset["token_url"]),
            "userinfo_url": site.get_str(f"oauth_{provider_id}_userinfo_url", preset["userinfo_url"]),
            "scope": site.get_str(f"oauth_{provider_id}_scope", preset["scope"]),
        }
    )
    config["enabled"] = site.get_bool(f"oauth_{provider_id}_enabled", False) and bool(config["client_id"])
    return config


def enabled_providers() -> list:
    if not site.get_bool("oauth_enabled", True):
        return []
    return [item for item in (provider_config(preset["id"]) for preset in PROVIDERS) if item and item["enabled"]]


def redirect_base() -> str:
    configured = site.get_str("oauth_redirect_base", "").strip()
    base = configured or site.get_str("site_url", "http://localhost:8080")
    return base.rstrip("/")


def callback_url(provider_id: str) -> str:
    return f"{redirect_base()}/api/auth/oauth/{provider_id}/callback"


def authorize_url(config: dict, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": config["client_id"],
            "redirect_uri": callback_url(config["id"]),
            "response_type": "code",
            "scope": config["scope"],
            "state": state,
        }
    )
    return f"{config['authorize_url']}?{query}"


def _http_json(url: str, data: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    body = None
    request_headers = {"Accept": "application/json", "User-Agent": "PhotonV"}
    if headers:
        request_headers.update(headers)
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=request_headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8", "ignore")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return dict(urllib.parse.parse_qsl(raw))


def exchange_code(config: dict, code: str) -> dict:
    try:
        payload = _http_json(
            config["token_url"],
            {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url(config["id"]),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"请求令牌失败：{exc}"}
    token = payload.get("access_token") or payload.get("accessToken")
    if not token:
        return {"error": payload.get("error_description") or payload.get("error") or "未取得访问令牌"}
    return {"accessToken": str(token)}


def fetch_profile(config: dict, access_token: str) -> dict:
    try:
        data = _http_json(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"获取用户信息失败：{exc}"}
    if not isinstance(data, dict):
        return {"error": "第三方返回的用户信息格式不正确"}
    provider_user_id = str(data.get("id") or data.get("sub") or data.get("user_id") or data.get("login") or "")
    if not provider_user_id:
        return {"error": "第三方返回的用户信息缺少 id"}
    email = str(data.get("email") or "")
    if not email and config["id"] == "github":
        try:
            emails = _http_json(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if isinstance(emails, list) and emails:
                primary = next((item for item in emails if item.get("primary")), emails[0])
                email = str(primary.get("email") or "")
        except Exception:  # noqa: BLE001
            pass
    return {
        "profile": {
            "providerUserId": provider_user_id,
            "username": str(data.get("login") or data.get("username") or data.get("name") or f"user{provider_user_id}"),
            "email": email,
            "avatar": str(data.get("avatar_url") or data.get("picture") or data.get("avatar") or ""),
            "raw": data,
        }
    }
