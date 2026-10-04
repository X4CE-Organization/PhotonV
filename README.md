# PhotonV · 开源微视频平台

<div align="center">

**一个开源、完整、开箱即用的微视频平台**

投稿 · 弹幕 · 评论 · 投币 · 收藏夹 · 合集 · 笔记 · 表情包 · 关注 · 分区 · 排行榜 · 消息 · 直播 · 会员 · 举报 · 管理后台 · 系统设置

**当前版本：1.4.3**

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
- [进阶能力配置](#进阶能力配置)
- [常见问题](#常见问题)
- [开源协议](#开源协议)

---

## 功能一览

### 用户侧

| 模块 | 能力 |
| --- | --- |
| **投稿** | 上传视频文件（带进度条）、填写外部直链、自动读取时长并**自动截取一帧作为封面**、手动换封面、选择分区、添加标签、设置是否允许评论 / 弹幕 / 下载 |
| **转码与清晰度** | 接 ffmpeg 自动转 360p / 480p / 720p 多清晰度 + HLS 分片，播放器可切换清晰度，后台能看到转码队列与失败原因 |
| **投稿管理** | 「我的投稿」支持按 全部 / 已公开 / 审核中 / 未通过 / 仅自己 筛选，可随时改为公开或私密、删除 |
| **播放器** | 自定义播放器：进度条、倍速（0.5x–2x）、全屏、下载（UP 主可关）、断点续播（自动上报进度） |
| **弹幕** | 滚动 / 顶部 / 底部三种模式，可选颜色、字号、不透明度、滚动速度，开关弹幕层；同一用户有发送间隔限制 |
| **评论** | 两级评论（回复自动归到主楼）、点赞、按最热 / 最新排序、UP 主可置顶、作者 / 管理员可删除 |
| **互动** | 点赞、投币（每人最多 2 个）、收藏到指定收藏夹、稍后再看、分享（复制链接并计数） |
| **收藏夹** | 多收藏夹、公开 / 私密、新建、重命名、删除（默认收藏夹不可删）、他人主页可看公开收藏 |
| **合集 / 播放列表** | 把多个视频整理成一个合集按顺序连播：新建 / 编辑 / 删除、增删视频、拖拽排序（接口层支持 reorder）、公开或私有；视频页一键加入合集，UP 主主页展示公开合集 |
| **视频笔记** | 边看边按时间点记笔记，点击时间戳可以跳回视频对应位置；每条笔记可单独设为公开或私密，个人中心可查看自己的全部笔记 |
| **表情包** | 上传图片 / GIF 制作自己的表情，评论框与私信里一键插入；「热门」里可以收藏别人发的表情（类似偷表情），表情以图片形式渲染在评论和私信里 |
| **@ 提及** | 评论里输入 `@用户名` 会高亮显示，并给被提到的人发一条通知 |
| **定时发布** | 投稿时可以指定发布时间（30 天内），到点后后台自动公开并通知作者 |
| **登录记录** | 个人设置里能看到最近 30 次登录的 IP、设备和时间，出现多个陌生 IP 时方便及时改密码 |
| **热搜词** | 搜索页展示站内真实热搜榜（按搜索次数统计，没有数据时用热门标签补齐） |
| **SEO** | 内置 `/sitemap.xml`（视频 / 分区 / 用户）、`/rss.xml` 订阅源、`/robots.txt`，方便被搜索引擎收录 |
| **关注** | 关注 / 取关、粉丝与关注列表、关注流（只看关注的人的新投稿） |
| **个人空间** | 头像、横幅、昵称、签名、等级与经验进度、投稿 / 粉丝 / 关注 / 总播放 / 获赞统计 |
| **观看历史** | 记录观看进度，显示看到哪里、什么时候看的 |
| **消息中心** | 回复我的、收到的赞、投币、新增粉丝、投稿审核、系统通知，未读红点，一键全部已读 |
| **搜索** | 视频（标题 + 简介）、用户（用户名 + 昵称）两类结果 |
| **排行榜** | 播放榜 / 点赞榜 / 投币榜 / 收藏榜 / 评论榜 / 粉丝榜，支持总榜与周榜 |
| **分区** | 频道导航（动画 / 游戏 / 知识 / 科技 / 生活 / 音乐 / 影视 / 美食 / 运动 / 舞蹈），分区内按最新 / 最多播放 / 最多点赞 / 最多投币 / 最多评论排序 |
| **举报** | 视频、评论、弹幕、用户都能举报，可选理由 + 补充说明，处理结果会收到通知 |
| **私信** | 一对一聊天：会话列表、未读红点、WebSocket 实时收消息、从个人空间一键发起 |
| **直播** | 直播间列表与直播中角标、播放器 + 实时聊天（WebSocket）、人气统计、推流密钥与推流 / 播放地址配置、开播下播 |
| **会员与充电** | 会员套餐（月 / 季 / 年）、硬币充值、给 UP 主充电（按比例分成）、订单记录与状态；管理端可审核订单、管理套餐 |
| **第三方登录** | GitHub / Gitee / Google / 自定义 OAuth2，支持自动注册、按邮箱绑定已有账号、个人中心绑定与解绑 |
| **邮件验证码** | SMTP 发信：注册邮箱验证、邮箱找回密码、订单与互动通知，用户可自行退订 |
| **手机号** | 短信验证码（阿里云 / 腾讯云 / 自定义网关 / 开发模式）、注册填手机号、手机号 + 验证码登录、个人设置绑定与解绑，手机号脱敏显示 |
| **在线支付** | 微信支付 v3（Native 扫码，RSA-SHA256 请求签名 + AES-256-GCM 回调解密）与支付宝（RSA2 签名，电脑网站支付跳转 / 当面付扫码 + 异步通知验签），下单后前端二维码轮询到账 |

### 管理侧

> 后台是一套独立的「控制台」：一行标题栏（当前位置 / 身份 / 回到前台）+ 一行标签栏（14 个模块按 总览 / 内容 / 用户 / 系统 分组，中间用竖线隔开，窄屏自动折行，不藏任何入口），下面是内容区。

| 模块 | 能力 |
| --- | --- |
| **运行总览** | 待办条（只有真的有活儿时才出现）、四项核心指标、近 14 天投稿横条趋势、服务健康状态（Redis / ffmpeg / 转码队列 / WebSocket）、最近管理动作时间线、最新注册、待审核投稿（有事才显示） |
| **视频审核** | 按状态与关键词筛选，一键通过 / 驳回（填写驳回原因并通知作者）、设为精选 / 置顶、关闭评论、删除，支持查看包含已删除 |
| **评论弹幕** | 搜索评论与弹幕、查看所属视频与时间点、单条删除 |
| **用户管理** | 搜索 / 角色 / 封禁状态筛选，编辑昵称与邮箱，封禁与解封，超管可调整角色、硬币与重置密码，删除用户 |
| **分区标签** | 分区增删改（名称 / 标识 / 图标 / 描述 / 排序 / 启用状态），标签使用量统计与清理 |
| **举报处理** | 待处理 / 已处理 / 已驳回筛选，三种处理方式：驳回举报、仅标记已处理、删除内容并处理（可连带封禁用户） |
| **直播管理** | 直播间状态（允许开播 / 强制下播 / 封禁 / 删除）、为指定用户开通直播权限 |
| **订单与会员** | 待处理订单审核（确认收款 / 驳回退款 / 退款）、会员套餐增删改、累计收入统计 |
| **缓存与转码** | Redis 连接状态、在线人数、缓存清理、ffmpeg 状态、转码队列（排队 / 转码中 / 完成 / 失败）、一键重新转码、WebSocket 连接数 |
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
| 前端 | **Vue 3 + TypeScript + Vite + Pinia + Vue Router + Tailwind CSS**（深色优先的扁平设计，图标全部为内置 SVG，不使用 emoji） |
| 转码 | **ffmpeg**（多清晰度 mp4 + HLS 分片，后台队列串行/并行处理） |
| 缓存与实时 | **Redis**（可选）：接口缓存、分布式限流、在线人数、Pub/Sub 多进程广播；**WebSocket** 用于私信与直播聊天 |
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
| ffmpeg | ≥ 4（可选） | 多清晰度转码与自动封面；不装则跳过转码 |
| Redis | ≥ 6（可选） | 缓存、分布式限流、在线人数、多进程实时广播 |

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
| `REDIS_URL` | 空 | Redis 连接串，如 `redis://localhost:6379`；留空则退回内置实现 |
| `CACHE_TTL_SECONDS` | `20` | 缓存时间（可在后台覆盖） |
| `FFMPEG_BIN` | 空 | ffmpeg 可执行文件路径，留空自动从 PATH 查找 |
| `TRANSCODE_ENABLED` | `true` | 上传后是否自动转码 |
| `TRANSCODE_CONCURRENCY` | `1` | 同时转码的任务数 |
| `HLS_SEGMENT_SECONDS` | `6` | HLS 分片长度 |
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
| 转码与清晰度 | 是否自动转码、生成 HLS、保留原文件、生成哪些清晰度 |
| 邮件 / SMTP | SMTP 服务器/端口/SSL/STARTTLS/账号/授权码、发件人与回复地址、发信节流、验证码间隔、注册邮箱验证、找回密码开关、五类邮件通知开关 |
| 第三方登录 | 总开关、自动注册、允许绑定、按邮箱绑定、登录页按钮、默认角色、回调前缀，以及 GitHub / Gitee / Google / 自定义四个提供方的启用与密钥、授权 / 令牌 / 用户信息地址、Scope |
| 会员与充电 | 会员开关、会员标识与权益说明、充值开关与兑换比例、充电开关与比例、创作者分成、可用支付方式、人工支付说明 |
| 直播 | 直播开关、开播是否需要权限、是否仅会员可开播、推流与播放地址前缀、提示语、聊天间隔与长度、单场最长时长 |
| 缓存与分布式 | 首页缓存时间、元数据缓存时间、在线人数统计窗口 |
| 短信 / 手机号 | 短信服务商（开发 / 阿里云 / 腾讯云 / 自定义）、AccessKey 与模板、验证码位数与有效期、发送间隔与每日上限、手机号登录开关、注册必填、必须绑定、前台脱敏 |
| 支付渠道 | 在线支付总开关、支付完成跳转、轮询间隔；支付宝 AppId / 应用私钥 / 支付宝公钥 / 网关 / 签名算法 / 支付方式；微信支付商户号 / AppId / APIv3 密钥 / 证书序列号 / 商户私钥 / 下单地址 |
| 视频与投稿 | 定时发布开关、合集开关、视频笔记开关与长度上限 |
| 注册与登录 | 注册需要邮箱 / 注册需要手机号两个独立开关（都不勾就是都选填，没勾的那项用户之后可在个人设置里自行绑定） |
| 社区与互动 | 自定义表情包开关、@ 提及开关、热搜词开关 |

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
| 合集 | `GET /api/playlists/mine` `POST /api/playlists` `PUT/DELETE /api/playlists/{id}` `GET /api/playlists/{id}` `POST/DELETE /api/playlists/{id}/items` `POST /api/playlists/{id}/reorder` `GET /api/users/{username}/playlists` |
| 笔记 | `GET/POST /api/videos/{id}/notes` `PUT/DELETE /api/notes/{id}` `GET /api/me/notes` |
| 表情包 | `GET /api/emojis` `GET /api/emojis/popular` `POST /api/emojis` `PUT/DELETE /api/emojis/{id}` `POST /api/emojis/{id}/collect` `POST /api/emojis/{id}/use` |
| 用户 | `GET /api/users/{username}` `/videos` `/followers` `/following` `/favorites` `/history` `POST /api/users/{username}/follow` |
| 站点 | `GET /api/settings` `GET /api/meta` `GET /api/home` `GET /api/categories` `GET /api/tags` `GET /api/search` `GET /api/search/hot` `GET /api/rank` `GET /api/following-feed` `GET /api/announcements` |
| SEO | `GET /sitemap.xml` `GET /rss.xml` `GET /robots.txt`（根路径，不带 `/api`） |
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

## 进阶能力配置

### 1. 转码与多清晰度（ffmpeg）

```bash
# Debian / Ubuntu
sudo apt install ffmpeg
# macOS
brew install ffmpeg
```

装好之后不用改任何配置：上传的视频会进入转码队列，依次产出
`360p / 480p / 720p`（源分辨率不足时自动跳过）与 `index.m3u8` HLS 分片，
产物放在 `data/processed/<视频 id>/`，播放器右上角会出现清晰度切换。

相关设置：后台 → 系统设置 → **转码与清晰度**；运行状态在 后台 → **缓存与转码** 里，
可以看到排队 / 转码中 / 完成 / 失败的数量，并能一键重新转码。
没有安装 ffmpeg 时状态会标记为 skipped，播放器直接用原始文件，不影响使用。

### 2. 直播（推流接入）

直播支持**两种开播方式**，都走同一套直播间与播放器，不用改前端：

| 方式 | 适合谁 | 协议 | 需要装软件 |
| --- | --- | --- | --- |
| **网页开播（浏览器直接推流）** | 所有主播 | WHIP（WebRTC） | 不用，网页里选屏幕 / 摄像头即可 |
| **OBS / 推流软件** | 需要多场景、采集卡、复杂音频的直播 | RTMP | 要 |

观众端同样两条路：WebRTC（WHEP，延迟 1 秒内，默认优先）与 HLS（兼容性最好，延迟 5-15 秒），
WebRTC 连不上会自动回退到 HLS。

#### 起一个媒体服务器（MediaMTX）

`docker-compose.yml` 里已经带了一个 MediaMTX 服务，配置文件是 `docs/mediamtx.yml`：

```bash
docker compose up -d mediamtx
```

它同时开放：

| 端口 | 用途 |
| --- | --- |
| 1935 | RTMP 推流（OBS） |
| 8888 | HLS 播放 |
| 8889 | WebRTC：WHIP 推流 + WHEP 播放 |
| 8189/udp | WebRTC 媒体端口 |
| 9997 | 管理 API，**只给内网**，不要暴露到公网 |

> 公网部署前，把 `docs/mediamtx.yml` 里的 `webrtcAdditionalHosts` 改成你的域名或公网 IP，
> 否则浏览器可能拿不到可用的候选地址。直播要在 HTTPS 下才能采集屏幕 / 摄像头。

#### 后台设置（后台 → 系统设置 → 直播）

| 设置 | 例子 | 说明 |
| --- | --- | --- |
| 启用内置推流接入 | 开 | 关掉就只能手填播放地址 |
| 允许 OBS 等 RTMP 推流 | 开 | |
| 允许网页开播 | 开 | |
| RTMP 推流服务器 | `rtmp://live.example.com:1935` | OBS 里的「服务器」 |
| 浏览器推流地址（WHIP） | `https://live.example.com` | |
| WebRTC 播放地址（WHEP） | `https://live.example.com` | |
| HLS 播放地址 | `https://hls.example.com` | |
| 媒体服务器 API 地址 | `http://mediamtx:9997` | 服务端查询推流状态用 |

这些值也可以用环境变量给默认值（`LIVE_API_URL` / `LIVE_RTMP_SERVER` / `LIVE_WHIP_BASE` /
`LIVE_WHEP_BASE` / `LIVE_HLS_BASE`），后台改过之后以数据库为准。

#### 主播怎么开播

进入「直播间 → 开播台」，两个页签：

* **网页开播**：选画面来源（屏幕共享 / 摄像头 / 屏幕+摄像头画中画）、
  选麦克风与摄像头、设分辨率和帧率，点「开始直播」。旁边实时显示上行码率、分辨率、帧率、丢包。
* **OBS 推流**：页面直接给出「服务器 + 串流密钥」，都有复制按钮，照着填进 OBS 即可；
  密钥泄露可以一键「重新生成」，旧的立刻失效。

#### 安全与自动化

* 推流鉴权走 MediaMTX 的 `authHTTPAddress` 回调到本项目的 `/api/live/mediamtx/auth`：
  **只有拿对串流密钥、且有开播权限的主播能推流**，密钥错了或没权限直接拒绝
* 后端每 5 秒向媒体服务器查一次「哪些路径正在推流」，主播断开后直播间会自动变回未开播，
  不需要手动点下播；同时能识别这路流是 OBS（RTMP）还是浏览器（WHIP）
* 单场最长时长、仅会员可开播、开播需管理员授权等策略沿用「直播」设置组

管理员可以在 后台 → 直播管理 里开播权限、强制下播或封禁直播间，
在 后台 → 缓存与转码 里能看到媒体服务器是否连通、当前有几路在推流。

> 直播开播台与 OBS 面板的实际界面：`docs/screenshot-live-studio.png`、`docs/screenshot-live-obs.png`。
>
> 想换成 SRS 5+ / nginx-rtmp 也可以：把它们的推流鉴权回调指到 `/api/live/mediamtx/auth`
> （接口只依赖 `action` 与 `path` 两个字段），再用 `/api/live/mediamtx/hooks/{ready|notready}`
> 让它们在上线 / 下线时通知本站即可。WebRTC 那两路（WHIP / WHEP）目前是 MediaMTX 才有的能力。

### 3. Redis（缓存与分布式）

```bash
sudo apt install redis-server     # 或 docker run -d -p 6379:6379 redis:7-alpine
# .env
REDIS_URL=redis://127.0.0.1:6379
```

启用后：首页与元数据走缓存、限流计数在多个进程间共享、在线人数按 5 分钟窗口统计、
私信与直播聊天的消息通过 Pub/Sub 在所有副本之间广播（所以可以直接多开副本做负载均衡）。
状态与缓存清理入口在 后台 → **缓存与转码**。

### 4. 邮件（SMTP）

后台 → 系统设置 → **邮件 / SMTP**：填服务器、端口、SSL/STARTTLS、账号、授权码、发件人，
保存后点「发送测试邮件」验证。能发：注册验证码、找回密码、订单通知、互动通知，
用户在 个人设置 → 邮件通知 里可以自行退订。

### 5. 第三方登录

后台 → 系统设置 → **第三方登录**，按需填写 GitHub / Gitee / Google 的
Client ID 与 Secret（自定义 OAuth2 还可以改授权、令牌、用户信息三个地址）。
回调地址形如 `https://你的域名/api/auth/oauth/github/callback`，
打开开关后登录页与注册页会自动出现对应按钮，个人设置里可以绑定 / 解绑。

### 6. 会员、充值与充电

后台 → 订单与会员 里维护会员套餐（名称 / 天数 / 价格 / 说明）与审核订单：

| 操作 | 效果 |
| --- | --- |
| 确认收款 | 会员订单按天数延长会员期；充值订单把硬币加到用户账户 |
| 驳回并退款 | 订单置为已取消（充电订单会把硬币退回买家） |
| 标记退款 | 订单置为已退款（充值订单会扣回硬币） |

支付方式默认是「人工审核 / 转账」，在下单页会显示收款说明；
要接真实网关，在 `backend/app/routers/orders.py` 的 `pay_order` 里把
在线支付分支替换成对应 SDK 的下单 + 异步回调即可（订单号 `order_no` 已生成好）。

## 常见问题

### 7. 手机号与短信

后台 → 系统设置 → **短信 / 手机号** 里选择服务商：

| 服务商 | 需要填写 | 说明 |
| --- | --- | --- |
| 开发模式（默认） | 无 | 验证码写进服务器日志与站内信，本地调试用，不花钱 |
| 阿里云短信 | AccessKeyId / AccessKeySecret / 签名 / TemplateCode | 模板变量名必须是 `code` |
| 腾讯云短信 | SecretId / SecretKey / SmsSdkAppId / 签名 / TemplateId | 模板变量个数填 1 |
| 自定义 HTTP 网关 | 网关地址 + 请求体模板 + 成功标识 | 模板支持 `{phone}` `{code}` `{sign}` `{template}`，响应里包含成功标识即视为成功 |

配置完成后可以在 后台 → 备份与维护 → **短信服务** 里发一条测试短信。
手机号登录开关、注册是否必填、是否必须绑定都在同一分组里。

### 8. 在线支付（微信支付 / 支付宝）

后台 → 系统设置 → **支付渠道**：

**支付宝（RSA2）**

| 参数 | 说明 |
| --- | --- |
| AppId | 开放平台应用的 AppId |
| 应用私钥 | 自己生成的 PKCS8 私钥（可整段粘贴，带不带 PEM 头都行） |
| 支付宝公钥 | 用于回调验签，从开放平台复制 |
| 支付方式 | `page` 电脑网站支付（跳转收银台）/ `qr` 当面付扫码（站内出二维码） |

**微信支付 v3（Native 扫码）**

| 参数 | 说明 |
| --- | --- |
| 商户号 mchid / AppId | 商户平台里的两个 ID |
| 商户证书序列号 | 商户 API 证书的序列号 |
| 商户 API 私钥 | `apiclient_key.pem` 的内容 |
| APIv3 密钥 | 32 位，用于回调解密 |

回调地址（填到两个平台的商户后台）：

```
https://你的域名/api/payments/alipay/notify
https://你的域名/api/payments/wechat/notify
```

支付流程：会员中心下单 → 选择支付宝 / 微信 → 跳转收银台或站内扫码 →
页面每 3 秒轮询一次订单状态 → 到账后自动刷新权益。
**回调会二次校验**：支付宝校验 RSA2 签名与金额，微信先 AES-GCM 解密再用
「主动查单」确认金额和状态，避免伪造通知。

> 没填网关参数时，下单会明确提示「未配置或未启用」，不会静默失败。

**Q：上传大文件失败？**
检查 `MAX_VIDEO_MB`、Nginx 的 `client_max_body_size`，以及磁盘剩余空间。
视频文件不会入库，只记录路径，所以迁移时记得一起搬 `data/` 目录。

**Q：视频没有封面？**
装了 ffmpeg 会自动截帧；没装的话浏览器会尝试截取一帧，都不行就在投稿页手动上传一张。

**Q：为什么投稿后看不到？**
默认开启「投稿需要审核后公开」，管理员在 后台 → 视频审核 通过后才会出现在首页；
审核结果会通过站内消息通知作者。想改成直接公开，把该设置关掉即可。

**Q：弹幕太多挡画面？**
后台「评论与弹幕」里可以调默认字号（建议 16-20）、不透明度和滚动速度，
观众也能在播放器上单独关闭弹幕层。

**Q：没有装 ffmpeg / Redis 会怎样？**
都不会影响使用：转码任务会标记为 skipped，播放器直接用原始文件；
Redis 缺失时缓存、限流、在线人数自动退回内置实现。

**Q：忘记超级管理员密码？**
用 Python 生成一个 PBKDF2 哈希替换数据库里的 `password_hash`：
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

### 1.4.0

- **直播接入重做，两种开播方式**：
  - **网页开播（浏览器直接推流）**：网页里直接选屏幕共享 / 摄像头 / 屏幕+摄像头画中画，
    选麦克风、分辨率、帧率、码率，点一下就能开播，不需要装任何软件（WebRTC / WHIP 推流）；
    开播中实时显示上行码率、分辨率、帧率与丢包
  - **OBS 等推流软件**：直播间里直接给出「服务器 + 串流密钥」，都带复制按钮，
    密钥可一键重置，旧密钥立刻失效
- **播放端**：优先 WebRTC（WHEP，延迟 1 秒内），连不上自动回退 HLS，播放器右上角会标出当前用的哪种
- **推流鉴权**：媒体服务器回调 `/api/live/mediamtx/auth`，只有拿对串流密钥、
  且有开播权限 / 符合会员与时长策略的主播才能推流，密钥错误直接拒绝
- **状态自动化**：后端每 5 秒同步一次媒体服务器状态，主播断开后直播间自动变为未开播，
  并能识别这路流是 OBS（RTMP）还是浏览器（WHIP）
- **部署**：`docker-compose.yml` 内置 MediaMTX 服务，配置在 `docs/mediamtx.yml`
  （已用 MediaMTX 1.11.3 实际启动验证过）；新增 `LIVE_*` 环境变量
- 系统设置「直播」分组细化为推流接入、地址、播放策略、画质上限等 12 项
- 后台「缓存与转码」新增直播接入状态（是否连通、当前几路推流）

### 1.4.3

- **全站排查「设计词汇串味」**：PhotonV 早期沿用了另一套后台的类名与配色
  （`card` 卡片、`text-slate-400/500` 灰阶、`-primary` 工具类），和 PhotonV 自己的
  `surface` / `muted` / `--pv-accent` 变量混在一起，看起来就像另一个项目。这次全部清掉：
  前台 13 个页面 + 后台 13 个面板 + 4 个组件，**残留 0 处**
- **新增统一的页面头**（`PageHead`）：图标 + 标题 + 一句说明，右侧放操作按钮，
  排行榜 / 收藏 / 关注 / 历史 / 消息 / 合集 / 分区 / 投稿 / 个人设置都已换上，
  不再是「一个裸标题 + 右侧一行小字」
- **个人设置页改版**：从单列堆卡片改成「左侧粘性资料卡（头像 / 昵称 / 等级 / 会员 /
  绑定状态）+ 右侧分栏设置」，和后台的系统设置页是同一套语言
- **修复设置图标画成了太阳**：`settings` 这个图标的路径原来是「圆圈 + 八条射线」，
  和 `sun` 完全一样，右上角菜单里的「设置」显示的是一颗太阳；已换成真正的齿轮
- 顶部进度条、弹幕进度条、弹幕设置面板、评论关闭提示等处的灰底也换成了主题变量

### 1.4.2

- **系统设置页按后台控制台的语言重做**，彻底换掉原来的「左侧分组卡片 + 右侧两列网格」：
  - 布局改成**一行一项**：设置项名称与说明在左，控件贴右；布尔项是开关，
    数字/下拉/颜色/图片/JSON 各自成行，不再挤在两列小格子里
  - 20 个分组在**同一页铺开**，左侧是锚点导航并跟随滚动高亮，不需要来回切分组
  - 顶部常驻搜索（设置项名称、键名、说明、所属分组都能匹配）
  - 底部悬浮「有 N 项未保存 · 放弃 · 保存」，改动过的行带高亮；JSON 项即时校验，格式不对不允许保存
- 补充 globe / palette / user-plus / message-square / shield-check / hard-drive /
  scale / key-round / phone 九个图标

### 1.4.1

- **后台排版重做**：去掉又高又重的深色横幅和「分组 + 模块」两层导航，
  改成一行标题栏 + 一行标签栏（14 个模块全部平铺，窄屏自动折行，不做横向滚动藏入口），
  后台首屏比以前少占约 90px 高度
- 总览页精简：待办条只在真的有活儿时才出现，待审核投稿列表没有内容时不再占版面
- 截图见 `docs/screenshot-admin-console.png` 与 `docs/screenshot-admin-content.png`

### 1.3.1

- 后台从「前台卡片式侧边栏」换成了独立的控制台界面（该版本的两层导航在 1.4.1 中已简化）
- **运行总览重做**：核心指标块、横向趋势条、服务健康状态、管理动作时间线、最新注册
- 后台内容区的面板标题与表格样式单独一套（左竖条标题 + 扁平表头）

### 1.3.0

- **合集 / 播放列表**：把多个视频整理成合集按顺序连播，支持新建 / 编辑 / 删除、
  增删视频、调整顺序、公开或私有；视频页一键加入合集，UP 主主页展示公开合集
- **视频笔记**：按时间点记笔记，点时间戳跳回视频对应位置，单条可设为公开或私密
- **表情包**：上传图片 / GIF 制作表情，评论框与私信一键插入，
  「热门」里可以收藏别人的表情；评论与私信以图片形式渲染表情
- **@ 提及**：评论里 `@用户名` 会高亮，并给对方发通知
- **定时发布**：投稿时指定发布时间（30 天内），到点自动公开并通知作者
- **登录记录**：个人设置里查看最近 30 次登录的 IP、设备与时间
- **热搜词**：搜索页展示站内真实热搜榜，无数据时用热门标签补齐
- **SEO**：新增 `/sitemap.xml`、`/rss.xml`、`/robots.txt`
- **注册必填项改为两个独立开关**：注册需要邮箱 / 注册需要手机号，都不勾则都选填，
  没勾的那一项用户之后可在个人设置里自行绑定
- 修复：`user_me()` 漏写 `return` 导致登录 / 注册 / 个人资料接口返回 `user: null`；
  投稿、评论、弹幕、举报的限流改到参数校验之后，表单填错不再白白进入冷却；
  健康检查接口的版本号与实际版本对齐

### 1.2.0

- **手机号**：短信验证码（阿里云 / 腾讯云 / 自定义 HTTP 网关 / 开发模式，签名全部用标准库实现）、
  注册填手机号、手机号 + 验证码登录、个人设置绑定与解绑、后台测试发送，手机号脱敏与唯一约束
- **真实在线支付**：微信支付 v3（Native 扫码 + RSA-SHA256 请求签名 + AES-256-GCM 回调解密 + 主动查单二次校验）
  与支付宝（RSA2 签名 + 电脑网站支付 / 当面付 + 异步通知验签 + 主动查单），
  会员中心可选支付方式、站内二维码与状态轮询，未配置网关时给出明确提示
- 订单表增加网关流水号与支付载荷；新增 `/api/payments/*` 与手机号相关接口
- 系统设置新增「短信 / 手机号」「支付渠道」两组（共 20 组 220+ 项）

### 1.1.0

- **转码与多清晰度**：接入 ffmpeg，上传后自动生成 360p / 480p / 720p 与 HLS 分片，
  播放器可切换清晰度，后台可查看转码队列、失败原因并一键重新转码
- **私信聊天**：会话列表、未读红点、WebSocket 实时收发，个人空间一键发起
- **直播间**：直播列表与直播中角标、播放器 + 实时聊天（WebSocket）、人气统计、
  推流密钥与推流 / 播放地址配置；后台可开播权限、强制下播、封禁与删除
- **会员 / 充值 / 充电**：会员套餐、硬币充值、给 UP 主充电（按比例分成）、订单中心与后台审核
- **第三方登录**：GitHub / Gitee / Google / 自定义 OAuth2，支持自动注册、邮箱绑定与解绑
- **邮件验证码**：SMTP 发信，注册邮箱验证、邮箱找回密码、订单与互动通知、用户退订
- **Redis 缓存与分布式**：首页 / 元数据缓存、分布式限流、在线人数、Pub/Sub 多进程广播
- **全新前端**：改成深色优先的侧边栏 + 顶栏布局，紫青渐变主色，全站图标替换为内置 SVG（不再使用 emoji）
- 弹幕默认字号从 25px 降到 18px，并支持在后台与播放器上调整
- 系统设置从 12 组扩到 **18 组 185+ 项**（新增转码、邮件、第三方登录、会员与充电、直播、缓存与分布式）

### 1.0.0

- 首个版本：投稿（含自动封面与上传进度）、弹幕（三种模式 + 颜色字号）、两级评论、点赞 / 投币 / 收藏夹 / 稍后再看 / 观看历史、关注与关注流、分区与标签、搜索、六类排行榜、消息中心、举报
- 管理后台：控制面板、视频审核（通过 / 驳回 / 精选 / 置顶）、评论弹幕管理、用户管理（封禁 / 角色 / 硬币 / 重置密码）、分区标签、举报处理、公告与轮播、操作与登录日志、备份与维护
- 系统设置后台自动渲染，支持按分组恢复默认；三种角色后端强校验
- 单镜像 Docker 部署，前端产物由后端托管
