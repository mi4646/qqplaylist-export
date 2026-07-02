# 贡献指南

感谢参与 qqplaylist-export！本指南帮你把开发环境跑起来。

## 前置依赖

- Python ≥ 3.10
- Node.js ≥ 18（前端构建用）
- Git

## 开发环境

后端（端口 8081，`--reload` 热重载）：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```

前端开发服务器（端口 8080，`/api` 代理到 127.0.0.1:8081）：

```bash
cd frontend
npm install
npm run serve      # http://localhost:8080
```

前端构建后，单独跑后端即可同时提供 API 与页面：

```bash
cd frontend && npm run build     # 产物到 frontend/dist
uvicorn app.main:app --port 8081  # http://localhost:8081
```

## 可用命令

### 前端（`frontend/`）

| 命令 | 说明 |
|------|------|
| `npm run serve` | 开发服务器，热重载，端口 8080 |
| `npm run build` | 生产构建，产物到 `frontend/dist` |
| `npm run lint` | ESLint 检查 |

### 后端（`backend/`）

| 命令 | 说明 |
|------|------|
| `uvicorn app.main:app --reload --port 8081` | 开发服务器，热重载 |
| `python app/qqmusic/sign.py` | 签名算法自检（无网络依赖，验证与 Go 参考向量对齐） |

### Docker

| 命令 | 说明 |
|------|------|
| `docker compose up -d --build` | 构建并后台启动（含健康检查/日志轮转/安全加固） |
| `docker build -t qqplaylist-export .` | 手动构建镜像 |

## 测试

本项目暂无自动化测试套件。签名算法是核心且脆弱的部分，改动 `backend/app/qqmusic/sign.py` 后务必跑自检：

```bash
python backend/app/qqmusic/sign.py
```

改动解析逻辑后，建议用一个公开歌单链接手动验证 `/api/playlist` 返回的 `songs_count` 与 `total_count` 是否一致。

## 代码风格

- 前端：`npm run lint`（ESLint + eslint-plugin-vue）
- 后端：遵循 PEP 8，类型注解与现有代码保持一致
- 改动遵循「最小变更」原则，详见仓库根 `CLAUDE.md`

## PR 提交清单

- [ ] 改动可追溯到具体需求或 bug
- [ ] 改动 `sign.py` 已跑 `python backend/app/qqmusic/sign.py` 自检通过
- [ ] 前端改动 `npm run lint` 无报错
- [ ] README / 文档已同步更新
- [ ] commit message 遵循 `type(scope): 描述` 格式（如 `feat(frontend): ...`、`fix(backend): ...`）
