# qqplaylist-export

将 QQ 音乐歌单链接解析为纯文本歌单（"歌名 - 歌手" 列表），供粘贴到 TuneMyMusic / Spotlistr 等工具迁移至 Apple / YouTube / Spotify。

后端：Python + FastAPI + httpx(async)。前端：Vue3 + Element Plus（位于 `frontend/`）。

## 接口

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
  "songs_count": 179
}
```

错误：HTTP 4xx，`{"detail": "中文错误信息"}`。

## 本地开发

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```

前端（开发服务器，`/api` 自动代理到 8081）：

```bash
cd frontend
npm install
npm run serve     # http://localhost:8080
```

前端构建（产物供后端托管）：

```bash
cd frontend
npm run build     # 产物到 frontend/dist
```

构建后单独跑后端即可同时提供 API 与页面：`uvicorn app.main:app --port 8081` → http://localhost:8081

## Docker

```bash
docker build -t qqplaylist-export .
docker run -p 8081:8081 qqplaylist-export
```

镜像内多阶段构建：node 编译前端 → python 运行后端并托管 `frontend/dist`。

## 说明

- 不缓存、不落库，每次请求实时调用 QQ 音乐 API。
- 签名算法移植自原 Go 版 `Encrypt`（md5 + 自定义 base64），见 `backend/app/qqmusic/sign.py`，含自检向量。
- 大歌单按 30 首/页分页，上限 10000 首。
