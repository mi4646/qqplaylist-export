# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

qqplaylist-export — 将 QQ 音乐歌单链接解析为纯文本歌单（"歌名 - 歌手" 列表），供迁移到 Apple/YouTube/Spotify。后端 Python + FastAPI + httpx(async)，前端 Vue3 + Element Plus（位于 `frontend/`）。无缓存、无数据库，每次请求实时调用 QQ 音乐 API。详见 `README.md` 与 `DESIGN.md`。

## 常用命令

后端开发（端口 8081，`--reload` 热重载）：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```

签名算法自检（无网络依赖，验证 sign 与 Go 版参考向量对齐）：

```bash
python backend/app/qqmusic/sign.py
```

前端开发服务器（端口 8080，`/api` 代理到 127.0.0.1:8081）：

```bash
cd frontend
npm install
npm run serve      # http://localhost:8080
npm run build      # 产物到 frontend/dist，供后端托管
npm run lint       # eslint
```

构建后单独跑后端即可同时提供 API 与页面：`uvicorn app.main:app --port 8081` → http://localhost:8081

Docker（多阶段：node 编译前端 → python 运行后端并托管 `frontend/dist`）：

```bash
docker build -t qqplaylist-export .
docker run -p 8081:8081 qqplaylist-export
```

环境变量：`HOST`（默认 `0.0.0.0`）、`PORT`（默认 `8081`）、`RATE_LIMIT`（默认 `10/minute`，slowapi 限流规则，作用于 `POST /api/playlist`，见 `backend/app/config.py`）。

限流：`backend/app/main.py` 用 slowapi 对 `/api/playlist` 限流，key 取 `X-Forwarded-For` 首段（云部署反代场景必需，nginx 需 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`），`/api/health` 不限流。

## 架构

请求流（单 API：`POST /api/playlist`）：

```
前端 App.vue → /api/playlist → main.playlist()
  → qqmusic/service.parse_playlist(url, detailed)
      → _extract_playlist_id()  解析 4 种链接形态（playlist/数字、id=数字、短链重定向、details 页）
      → client.fetch_page()     分页拉取（30首/页，上限 10000）
      → _build_song_list()      标准化歌名 + 拼接 "歌名 - 歌手"
  → main._format_songs()        按 format 调整顺序/裁剪
  → 按 order 反转
```

关键点（跨多文件、非显而易见）：

- **签名算法是核心且脆弱**：`backend/app/qqmusic/sign.py` 的 `encrypt()` 移植自 Go 版，必须与 QQ 音乐服务端字节级对齐。修改后务必跑 `python sign.py` 自检向量。`sign.py` 末尾的 `ponytail:` 注释说明：原 Go 版用 `strings.ReplaceAll(t2, "[\\/+]","")` 做的是字面量替换（base64 字母表不含 `[]`，实为 no-op），Python 版保持一致以对齐生产签名——不要"修正"成正则。

- **平台参数容错**：`client.PLATFORMS` 列表依次尝试，QQ 音乐对失败请求返回**恰好 108 字节**的响应（`ERROR_RESPONSE_LENGTH`），以此为失败判据换平台重试，而非依赖错误码/JSON 字段。

- **请求体 JSON 必须紧凑**：`build_request_body` 用 `separators=(",", ":")`，字段顺序与 Go 版一致——签名基于原始字符串，空格/顺序变化会导致签名失效。

- **静态托管挂载顺序**：`main.py` 末尾 `app.mount("/", StaticFiles(...))` 必须在 API 路由之后，否则会拦截 `/api/*`。仅在 `frontend/dist` 存在时挂载。

- **链接解析的递归**：`_extract_playlist_id` 对短链（含 `fcgi-bin`）通过 `get_redirect_location`（不跟随跳转）取 Location 后递归解析。

- **歌名标准化**：`_standard_song_name` 把中文括号转英文括号（左括号前补空格）、去 `【...】`；`detailed=true` 时跳过标准化保留原名。`format`/`order` 在 `main.py` 层处理，与解析解耦。

## 错误处理约定

业务错误用 `QQMusicError`（`service.py`），在 `main.py` 转为 HTTP 400 + 中文 `detail`。前端据此展示。网络/分页失败在 `_fetch_playlist_data` 中按页吞掉并记日志，尽量返回已获取部分。
