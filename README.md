# qqplaylist-export

把 QQ 音乐歌单一键导出成纯文本歌单（「歌名 - 歌手」列表），方便粘贴到 TuneMyMusic / Spotlistr 等工具，迁移到 Apple Music / YouTube Music / Spotify。

提供网页界面，也提供 HTTP API。后端 Python + FastAPI，前端 Vue3 + Element Plus。

## 功能

- 粘贴 QQ 音乐歌单链接，一键解析出全部歌曲文本
- 支持大歌单（自动分页，上限 10000 首）
- 可选格式：`歌名 - 歌手` / `歌手 - 歌名` / 仅歌名
- 可选顺序：正序 / 倒序
- 可选保留原始歌名（不去括号、不去标记）
- 一键复制结果，或下载为 TXT（文件名取歌单名）
- 实时调用，不缓存、不落库

## 快速开始

### 用 Docker（最简单）

```bash
docker build -t qqplaylist-export .
docker run -p 8081:8081 qqplaylist-export
```

或用 docker compose（已配置健康检查、日志轮转、安全加固）：

```bash
docker compose up -d --build
```

打开 http://localhost:8081 ，把歌单链接粘进页面即可。

### 本地开发

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```

前端开发服务器（`/api` 自动代理到 8081）：

```bash
cd frontend
npm install
npm run serve     # http://localhost:8080
```

前端构建后，单独跑后端即可同时提供 API 与页面：

```bash
cd frontend && npm run build     # 产物到 frontend/dist
uvicorn app.main:app --port 8081  # http://localhost:8081
```

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `0.0.0.0` | 后端监听地址，容器内通常保持默认 |
| `PORT` | `8081` | 后端监听端口；docker compose 同时以此端口对外暴露。注意 `cap_drop: ALL` 下不能 `<1024`，需 80/443 请用反代 |
| `RATE_LIMIT` | `10/minute` | slowapi 限流规则，作用于 `POST /api/playlist`；`/api/health` 不限流 |

docker compose 会自动读取同目录 `.env`，也可直接前缀：`PORT=9000 docker compose up`。

## 背景

本项目参考 [Bistutu/GoMusic](https://github.com/Bistutu/GoMusic) 的 Python 版本，并修复了其**歌单数量识别不准**的问题：原版在大歌单分页时，遇到单页失败会整页丢弃，导致总数十首几十首地少（例如总数 950 首只解析出 930 首）。

本仓库改为整页失败时逐步拆小重试，仅在单首确实取不到（下架/区域限制）时才放弃该首，并把原始总数与实际解析数一并返回，缺失一目了然。详见 `backend/app/qqmusic/client.py` 的 `fetch_page_resilient`。

## HTTP API

`POST /api/playlist`

```json
// 请求体
{
  "url": "https://i.y.qq.com/playlist?id=7364061065",
  "detailed": false,
  "format": "song-singer",
  "order": "normal"
}
```

| 字段 | 取值 |
|------|------|
| `detailed` | `true` 保留原始歌名（不去括号）；默认 `false` |
| `format` | `song-singer`(默认) / `singer-song` / `song` |
| `order` | `normal`(默认) / `reverse` |

```json
// 响应 200
{
  "name": "歌单标题",
  "songs": ["歌名 - 歌手", "..."],
  "songs_count": 179,
  "total_count": 179
}
```

- `songs_count`：实际解析出的歌曲数
- `total_count`：QQ 音乐返回的歌单原始总数；正常等于 `songs_count`，若个别歌曲下架/被限制则会偏大，差值即缺失数

错误：HTTP 4xx，`{"detail": "中文错误信息"}`。

健康检查：`GET /api/health`（不限流）。

## 说明

- 签名算法移植自原 Go 版 `Encrypt`（md5 + 自定义 base64），见 `backend/app/qqmusic/sign.py`，含自检向量，可用 `python backend/app/qqmusic/sign.py` 验证。
- 限流按客户端 IP 限制；直连部署（如云服务器直接暴露端口）即开即用。若自行在前面再加一层 nginx 反代，需配置 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` 透传客户端 IP，否则限流会按代理 IP 误伤全局。
