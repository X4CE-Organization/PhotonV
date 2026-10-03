# PhotonV · 开源微视频平台

<div align="center">

**一个开源、完整、开箱即用的微视频平台**

投稿 · 弹幕 · 评论 · 投币 · 收藏夹 · 关注 · 分区 · 排行榜 · 消息 · 举报 · 管理后台 · 系统设置

**当前版本：1.0.0**

</div>

---

## 目录

- [功能一览](#功能一览)
- [角色与权限](#角色与权限)
- [技术栈](#技术栈)
- [快速部署（源码方式）](#快速部署源码方式)
- [Docker 部署](#docker-部署)
- [环境变量](#环境变量)
- [首次登录与默认账号](#首次登录与默认账号)
- [目录结构](#目录结构)
- [系统设置](#系统设置)
- [接口概览](#接口概览)
- [备份、升级与维护](#备份升级与维护)
- [常见问题](#常见问题)
- [开源协议](#开源协议)

---

## 功能一览

### 用户侧

| 模块 | 能力 |
| --- | --- |
| **投稿** | 上传视频文件（带进度条）、填写外部直链、自动读取时长并**自动截取一帧作为封面**、手动换封面、选择分区、添加标签、设置是否允许评论 / 弹幕 / 下载 |
| **投稿管理** | 「我的投稿」支持按 全部 / 已公开 / 审核中 / 未通过 / 仅自己 筛选，可随时改为公开或私密、删除 |
| **播放器** | 自定义播放器：进度条、倍速（0.5x–2x）、全屏、下载（UP 主可关）、断点续播（自动上报进度） |
| **弹幕** | 滚动 / 顶部 / 底部三种模式，可选颜色、字号、不透明度、滚动速度，开关弹幕层；同一用户有发送间隔限制 |
| **评论** | 两级评论（回复自动归到主楼）、点赞、按最热 / 最新排序、UP 主可置顶、作者 / 管理员可删除 |
| **互动** | 点赞、投币（每人最多 2 个）、收藏到指定收藏夹、稍后再看、分享（复制链接并计数） |
| **收藏夹** | 多收藏夹、公开 / 私密、新建、重命名、删除（默认收藏夹不可删）、他人主页可看公开收藏 |
| **关注** | 关注 / 取关、粉丝与关注列表、关注流（只看关注的人的新投稿） |
| **个人空间** | 头像、横幅、昵称、签名、等级与经验进度、投稿 / 粉丝 / 关注 / 总播放 / 获赞统计 |
| **观看历史** | 记录观看进度，显示看到哪里、什么时候看的 |
| **消息中心** | 回复我的、收到的赞、投币、新增粉丝、投稿审核、系统通知，未读红点，一键全部已读 |
| **搜索** | 视频（标题 + 简介）、用户（用户名 + 昵称）两类结果 |
| **排行榜** | 播放榜 / 点赞榜 / 投币榜 / 收藏榜 / 评论榜 / 粉丝榜，支持总榜与周榜 |
| **分区** | 频道导航（动画 / 游戏 / 知识 / 科技 / 生活 / 音乐 / 影视 / 美食 / 运动 / 舞蹈），分区内按最新 / 最多播放 / 最多点赞 / 最多投币 / 最多评论排序 |
| **举报** | 视频、评论、弹幕、用户都能举报，可选理由 + 补充说明，处理结果会收到通知 |

### 管理侧

| 模块 | 能力 |
| --- | --- |
| **控制面板** | 用户 / 视频 / 播放 / 弹幕 / 评论 / 投币 / 举报等关键指标，近 14 天投稿趋势，待审核视频，最近管理操作，最新注册用户 |
| **视频管理** | 按状态与关键词筛选，一键通过 / 驳回（填写驳回原因并通知作者）、设为精选 / 置顶、关闭评论、删除，支持查看包含已删除 |
| **评论弹幕** | 搜索评论与弹幕、查看所属视频与时间点、单条删除 |
| **用户管理** | 搜索 / 角色 / 封禁状态筛选，编辑昵称与邮箱，封禁与解封，超管可调整角色、硬币与重置密码，删除用户 |
| **分区标签** | 分区增删改（名称 / 标识 / 图标 / 描述 / 排序 / 启用状态），标签使用量统计与清理 |
| **举报处理** | 待处理 / 已处理 / 已驳回筛选，三种处理方式：驳回举报、仅标记已处理、删除内容并处理（可连带封禁用户） |
| **公告 / 轮播** | 公告置顶与公开开关，首页轮播增删改与启用状态 |
| **系统设置** | 12 个分组、110+ 项设置，全部可在线修改、支持按分组恢复默认 |
| **日志** | 操作日志（谁在什么时候做了什么）、登录日志（成功与失败的 IP、UA） |
| **备份与维护** | 一键 `pg_dump` 备份、查看与删除备份、清理过期日志与限流记录、运行状态 |

---

## 角色与权限

| 角色 | 权限 |
| --- | --- |
| **普通用户** | 投稿、评论、发弹幕、点赞、投币、收藏、关注、举报、管理自己的内容 |
| **管理员** | 普通用户的全部权限，外加：视频审核、评论弹幕管理、举报处理、用户管理（封禁 / 解封）、分区标签、公告与轮播 |
| **超级管理员** | 管理员的全部权限，外加：系统设置、角色分配、硬币调整、密码重置、删除用户、操作日志、备份与维护 |

> 权限只由后端校验，前端隐藏菜单只是为了体验；每个管理接口都会再校验一次角色。

---

## 技术栈

| 层次 | 选型 |
| --- | --- |
| 后端 | **Python 3.10+ / FastAPI / SQLAlchemy 2.0**（原生 ESM 风格的 async 框架 + ORM） |
| 数据库 | **PostgreSQL 14+** |
| 前端 | **Vue 3 + TypeScript + Vite + Pinia + Vue Router + Tailwind CSS** |
| 鉴权 | 自实现 HS256 JWT（标准库 hmac/hashlib）+ PBKDF2-SHA256 密码哈希，**无第三方加密依赖** |
| 弹幕 | 自研 DOM 弹幕引擎（轨道分配 + CSS 动画），无第三方播放器依赖 |
| 上传 | FastAPI `UploadFile` 流式写盘，前端 XHR 显示上传进度 |
| 部署 | 单进程（API + 前端静态托管），也可 Docker 一键部署 |

> 前端构建产物由后端直接托管，**生产环境只需要一个进程、一个端口**。

---

## 快速部署（源码方式）

### 1. 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Python | ≥ 3.10（3.9 亦可） | 后端运行时 |
| Node.js | ≥ 20 | 构建前端 |
| PostgreSQL | ≥ 14 | 数据库 |
| pg_dump | 与数据库版本匹配 | 后台备份功能需要 |

### 2. 获取代码并安装依赖

```bash
git clone https://github.com/x4ce-organization/PhotonV.git
cd PhotonV

# 后端
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt        # 国内可加 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前端
cd frontend && npm install && cd ..            # 国内可加 --registry=https://registry.npmmirror.com
```

### 3. 准备数据库与配置

```bash
sudo -u postgres psql -c "CREATE USER photonv WITH PASSWORD 'photonv';"
sudo -u postgres psql -c "CREATE DATABASE photonv OWNER photonv;"

cp .env.example .env
openssl rand -hex 48     # 生成 SECRET_KEY
```

### 4. 构建并启动

```bash
cd frontend && npm run build && cd ..                  # 构建前端
cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

浏览器打开 `http://localhost:8080`。首次启动会自动建表并写入示例数据
（超级管理员、10 个分区、3 个示例用户、6 条示例视频、示例公告与轮播）。

### 5. 开发模式

```bash
# 终端 1：后端（自动重载）
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8080

# 终端 2：前端（热更新，自动代理 /api 与 /media 到 8080）
cd frontend && npm run dev
```

### 6. 使用 systemd 常驻（Linux 示例）

```ini
# /etc/systemd/system/photonv.service
[Unit]
Description=PhotonV
After=network.target postgresql.service

[Service]
Type=simple
User=photonv
WorkingDirectory=/opt/PhotonV
EnvironmentFile=/opt/PhotonV/.env
ExecStart=/opt/PhotonV/.venv/bin/python -m uvicorn app.main:app --app-dir /opt/PhotonV/backend --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now photonv
```

Nginx 反向代理要注意放开上传体积：`client_max_body_size 2048m;`，
并把 `proxy_read_timeout` 调大，否则大文件上传会中断。

---

## Docker 部署

```bash
cp .env.example .env      # 至少修改 POSTGRES_PASSWORD 与 SECRET_KEY
docker compose up -d --build
```

国内服务器构建慢的话，在 `.env` 里加：

```
APT_MIRROR=mirrors.aliyun.com
PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

compose 会启动两个容器：`photonv-db`（PostgreSQL）与 `photonv`（应用 + 前端），
上传的视频、封面、备份都落在宿主机的 `./data` 目录。

---

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` / `HOST` | `8080` / `0.0.0.0` | 服务监听地址 |
| `SITE_URL` | `http://localhost:8080` | 站点对外地址 |
| `SECRET_KEY` | — | **必须修改**，JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_DAYS` | `14` | 登录有效期 |
| `DATABASE_URL` | `postgresql+psycopg://photonv:photonv@localhost:5432/photonv` | 数据库连接串 |
| `DATA_DIR` | `./data` | 视频、封面、头像、备份的存放目录 |
| `MAX_VIDEO_MB` | `2048` | 单个视频体积上限 |
| `MAX_IMAGE_MB` | `16` | 单张图片体积上限 |
| `ROOT_USERNAME` / `ROOT_PASSWORD` | `root` / `photonv123456` | 初始化时创建的超级管理员 |

> 注意：`ROOT_*` 只在**数据库里没有任何用户**时生效，改密码请登录后在个人设置里改。

---

## 首次登录与默认账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| `root` | `photonv123456` | 超级管理员 |
| `alice` / `bob` / `carol` | `photonv123456` | 示例普通用户 |

> 请首次登录后立刻修改密码，并在 `.env` 里更换 `SECRET_KEY`。
> 站点前台不会展示「谁是超级管理员」这类信息。

---

## 目录结构

```
PhotonV/
├── backend/                     # FastAPI 后端
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # 应用入口：中间件、静态资源、路由注册
│       ├── config.py            # 环境变量与目录配置
│       ├── database.py          # 引擎、会话、备份
│       ├── models.py            # SQLAlchemy 数据模型
│       ├── security.py          # 密码哈希、JWT、鉴权依赖
│       ├── settings_registry.py # 所有可配置项（后台自动渲染）
│       ├── settings_store.py    # 设置读写与缓存
│       ├── utils.py             # 分页、序列化、审计、通知、限流
│       ├── seed.py              # 初始化数据
│       └── routers/             # auth / users / videos / comments / danmaku /
│                                # interactions / public / notifications /
│                                # reports / uploads / admin
├── frontend/                    # Vue 3 前端
│   └── src/
│       ├── components/          # 播放器、弹幕、评论、视频卡片…
│       ├── views/               # 首页、视频页、投稿、空间、搜索…
│       │   └── admin/           # 管理后台各页面
│       ├── api.ts / store.ts / router.ts / utils.ts
├── docs/demo/                   # 示例视频（CC0）
├── data/                        # 运行期数据（不入库）
├── Dockerfile / docker-compose.yml
└── .env.example
```

---

## 系统设置

后台「系统设置」共 12 个分组、110+ 项，全部带类型校验（字符串 / 数字范围 / 开关 / 下拉 / JSON / 颜色 / 图片）：

| 分组 | 主要内容 |
| --- | --- |
| 站点信息 | 站点名称、全称、描述、关键词、Logo、图标、备案号、开源仓库地址 |
| 外观布局 | 主题色、默认配色、是否允许深色模式、页面宽度、首页轮播与间隔、公告条、推荐位数量、首页排行榜、页脚文字、版权 |
| 注册与登录 | 注册开关、邮箱要求与后缀白名单、邀请码、默认角色、用户名与密码规则、会话时长、登录失败锁定、是否允许改用户名 |
| 用户与权限 | 个人主页开关、默认隐私、关注开关、私信开关、注册赠送硬币、每日登录硬币、等级经验与名称、用户列表分页 |
| 视频与投稿 | 投稿开关与等级要求、是否审核、投稿说明、标题与简介长度、标签数量、分页、投稿间隔与每日上限、允许的视频与图片格式、是否允许下载、播放器自动播放与清晰度、播放计数规则、播放经验 |
| 评论与弹幕 | 评论开关、长度、间隔、默认排序、分页、是否审核；弹幕开关、长度、间隔、不透明度、滚动速度 |
| 社区与互动 | 回复 / 点赞 / 关注 / 投币 / 审核通知开关、举报开关与举报理由、分享按钮 |
| 内容审核 | 敏感词、命中后是否直接驳回、被举报自动隐藏与阈值、保留用户名 |
| 存储与上传 | 视频与图片体积上限、是否允许外部直链、是否保留原文件 |
| 安全防护 | 维护模式与提示语、维护时是否放行管理员、每 IP 每分钟请求上限、验证码、IP 黑名单、强制 HTTPS、内容安全提示 |
| 备份与维护 | 自动备份与间隔、保留份数、审计日志开关、登录日志保留天数、首页缓存时间 |
| 页脚与协议 | 关于我们、用户协议、隐私政策、联系邮箱 |

---

## 接口概览

启动后访问 `/api/docs` 可以看到完整的 OpenAPI 文档（Swagger UI）。

| 分类 | 主要接口 |
| --- | --- |
| 认证 | `POST /api/auth/register` `POST /api/auth/login` `GET /api/auth/me` `PUT /api/auth/profile` `PUT /api/auth/password` `GET /api/auth/check-username` |
| 视频 | `GET /api/videos` `GET /api/videos/{id}` `POST /api/videos` `PUT /api/videos/{id}` `DELETE /api/videos/{id}` `POST /api/videos/{id}/visibility` `GET /api/videos/{id}/related` |
| 弹幕 | `GET /api/videos/{id}/danmaku` `POST /api/videos/{id}/danmaku` `DELETE /api/danmaku/{id}` |
| 评论 | `GET /api/videos/{id}/comments` `POST /api/videos/{id}/comments` `POST /api/comments/{id}/like` `POST /api/comments/{id}/pin` `DELETE /api/comments/{id}` |
| 互动 | `POST /api/videos/{id}/like` `.../coin` `.../favorite` `.../watch-later` `.../progress` `GET /api/me/watch-later` `GET /api/me/favorite-folders` |
| 用户 | `GET /api/users/{username}` `/videos` `/followers` `/following` `/favorites` `/history` `POST /api/users/{username}/follow` |
| 站点 | `GET /api/settings` `GET /api/meta` `GET /api/home` `GET /api/categories` `GET /api/tags` `GET /api/search` `GET /api/rank` `GET /api/following-feed` `GET /api/announcements` |
| 上传 | `POST /api/upload/video` `POST /api/upload/image` `POST /api/upload/avatar` |
| 消息 / 举报 | `GET /api/notifications` `POST /api/notifications/read` `POST /api/reports` `GET /api/reports/mine` |
| 管理 | `/api/admin/dashboard` `/users` `/videos` `/comments` `/danmaku` `/categories` `/tags` `/reports` `/announcements` `/carousel` `/settings` `/logs/audit` `/logs/login` `/backups` `/maintenance/cleanup` |

---

## 备份、升级与维护

```bash
# 备份（后台「备份与维护」里一键操作，或手动）
pg_dump --no-owner --no-privileges -f data/backups/photonv.sql "$DATABASE_URL"

# 恢复
psql "$DATABASE_URL" -f data/backups/photonv.sql

# 升级
git pull
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
sudo systemctl restart photonv
```

数据库结构由 SQLAlchemy 在启动时自动创建（幂等），新增字段写在
`backend/app/schema` 对应的模型里即可，老库会自动补表。

---

## 常见问题

**Q：上传大文件失败？**
检查 `MAX_VIDEO_MB`、Nginx 的 `client_max_body_size`，以及磁盘剩余空间。
视频文件不会入库，只记录路径，所以迁移时记得一起搬 `data/` 目录。

**Q：视频没有封面？**
浏览器不支持自动截帧时（例如某些编码），在投稿页手动上传一张即可。

**Q：为什么投稿后看不到？**
默认开启「投稿需要审核后公开」，管理员在 后台 → 视频审核 通过后才会出现在首页；
审核结果会通过站内消息通知作者。想改成直接公开，把该设置关掉即可。

**Q：弹幕太多卡顿？**
弹幕接口一次最多返回 5000 条，可以在「评论与弹幕」分组里调低不透明度或直接关闭弹幕层。

**Q：忘记超级管理员密码？**
在数据库里把 `users.username` 对应行的 `password_hash` 置空后用初始化脚本重建，
或直接用 Python 生成一个 PBKDF2 哈希替换：
`python -c "from app.security import hash_password; print(hash_password('新密码'))"`。

---

## 开源协议

本项目以 **AGPL-3.0** 协议开源，见 [LICENSE](./LICENSE)。

仓库地址：<https://github.com/x4ce-organization/PhotonV>

Copyright © 2026 X4CE

### 商业使用要求（必读）

**任何商业使用都必须保留指向本仓库的署名与链接**：

- **必须保留署名**：页脚、关于页面或随附文档中至少有一处明显可见地写着「Powered by PhotonV」，
  并链接到 <https://github.com/x4ce-organization/PhotonV>；不得删除、隐藏或改成别的地址
- **适用范围**：对外提供付费服务、集成进商业产品、二次分发、以本项目为基础搭建托管服务等
- **不得移除版权与作者信息**
- **需要例外授权**：想去掉署名或闭源分发，请联系仓库作者单独获取许可

---

## 更新日志

### 1.0.0

- 首个版本：投稿（含自动封面与上传进度）、弹幕（三种模式 + 颜色字号）、两级评论、点赞 / 投币 / 收藏夹 / 稍后再看 / 观看历史、关注与关注流、分区与标签、搜索、六类排行榜、消息中心、举报
- 管理后台：控制面板、视频审核（通过 / 驳回 / 精选 / 置顶）、评论弹幕管理、用户管理（封禁 / 角色 / 硬币 / 重置密码）、分区标签、举报处理、公告与轮播、操作与登录日志、备份与维护
- 系统设置 12 个分组 110+ 项，后台自动渲染，支持按分组恢复默认
- 三种角色（普通用户 / 管理员 / 超级管理员）后端强校验
- 单镜像 Docker 部署，前端产物由后端托管
