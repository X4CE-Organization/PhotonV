"""PhotonV 应用入口：中间件、静态资源与路由注册。"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import redis_client as redis
from . import settings_store as site
from . import realtime, transcode
from .config import settings
from .database import SessionLocal, init_db
from .routers import (
    admin,
    auth,
    comments,
    danmaku,
    emojis,
    interactions,
    live,
    mail,
    messages,
    notes,
    notifications,
    oauth,
    orders,
    payments,
    phone,
    playlists,
    public,
    reports,
    seo,
    uploads,
    users,
    videos,
    ws,
)

app = FastAPI(title="PhotonV API", version="1.3.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_hits: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def guard(request: Request, call_next):
    path = request.url.path
    ip = request.client.host if request.client else "unknown"

    blocked = site.get_json("blocked_ips", []) or []
    if blocked and ip in blocked:
        return JSONResponse(
            status_code=403, content={"code": "IP_BLOCKED", "message": "你的 IP 已被限制访问"}
        )

    # 记录在线用户（Redis 可用时按 5 分钟窗口统计）
    token = request.headers.get("authorization") or ""
    if token.lower().startswith("bearer "):
        from .security import decode_token

        payload = decode_token(token[7:].strip())
        if payload and payload.get("sub"):
            redis.touch_online(int(payload["sub"]))

    # 简单滑动窗口限流
    limit = site.get_int("rate_limit_per_minute", 1200)
    if limit > 0 and path.startswith("/api"):
        now_ts = time.time()
        bucket = _hits[ip]
        bucket[:] = [stamp for stamp in bucket if now_ts - stamp < 60]
        bucket.append(now_ts)
        if len(bucket) > limit:
            return JSONResponse(
                status_code=429, content={"code": "TOO_MANY", "message": "请求过于频繁，请稍后再试"}
            )
        if len(_hits) > 5000:
            for key in [k for k, v in _hits.items() if not v or now_ts - v[-1] > 300]:
                _hits.pop(key, None)

    if site.get_bool("maintenance_mode", False) and not path.startswith(("/api/admin", "/api/auth", "/api/settings", "/api/health")):
        allow_admin = site.get_bool("maintenance_allow_admin", True)
        if not allow_admin:
            return JSONResponse(
                status_code=503,
                content={"code": "MAINTENANCE", "message": site.get_str("maintenance_message", "站点维护中")},
            )

    response = await call_next(request)
    response.headers["X-Powered-By"] = "PhotonV"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        payload = {"code": detail.get("code", "ERROR"), "message": detail.get("message", "请求失败")}
    else:
        payload = {"code": "HTTP_ERROR", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": "BAD_REQUEST", "message": "请求参数不正确", "detail": exc.errors()})


@app.get("/api/health")
def health():
    return {"ok": True, "name": site.get_str("site_name", "PhotonV"), "version": "1.3.0"}


for module in (
    public,
    auth,
    oauth,
    mail,
    users,
    videos,
    playlists,
    notes,
    comments,
    danmaku,
    emojis,
    interactions,
    messages,
    phone,
    payments,
    live,
    orders,
    notifications,
    reports,
    seo,
    uploads,
    ws,
    admin,
):
    app.include_router(module.router)

# 静态资源：data/ 下的视频、封面、头像
settings.ensure_dirs()
app.mount("/media", StaticFiles(directory=str(settings.data_dir)), name="media")

# 前端构建产物（存在时由后端直接托管）
if settings.frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(settings.frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "接口不存在"})
        candidate = settings.frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(settings.frontend_dist / "index.html")


@app.on_event("startup")
def on_startup() -> None:
    settings.ensure_dirs()
    init_db()
    db = SessionLocal()
    try:
        site.warm(db)
        from .seed import ensure_seed

        ensure_seed(db)
        site.warm(db)
    finally:
        db.close()
    redis.init()
    redis.subscribe_worker(realtime.deliver_local)
    transcode.start_worker()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=not settings.is_prod)


if __name__ == "__main__":
    run()
