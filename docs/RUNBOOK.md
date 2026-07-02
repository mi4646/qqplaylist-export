# Runbook

qqplaylist-export 运维手册。无状态服务：无缓存、无数据库，每次请求实时调用 QQ 音乐 API。

## 部署

### Docker Compose（推荐）

```bash
docker compose up -d --build
```

compose 已配置：
- **健康检查**：每 30s 用容器内 `python` 探 `GET /api/health`，5s 超时，连续 3 次失败标记 unhealthy，启动缓冲 10s
- **日志轮转**：json-file 驱动，单文件 10MB、保留 3 个
- **安全加固**：`cap_drop: ALL` + `no-new-privileges` + `init: true`（tini 做 PID 1）
- **重启策略**：`unless-stopped`（容器退出时重启，但不响应 unhealthy）

### 端口选择

`PORT` 默认 8081。**不能 < 1024**——`cap_drop: ALL` 移除了 `CAP_NET_BIND_SERVICE`，绑定 80/443 会 `Permission denied` 进入崩溃循环。需 80/443 请在前端加 nginx 反代。

## 配置

环境变量（见 README 表）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8081` | 监听端口，≥1024 |
| `RATE_LIMIT` | `10/minute` | `POST /api/playlist` 限流；`/api/health` 不限流 |

通过同目录 `.env` 或前缀注入：`PORT=9000 docker compose up`。

## 健康检查与监控

### 端点

- `GET /api/health` → `200 {"status":"ok"}`，不限流，供 LB/监控探活
- `POST /api/playlist` → 业务接口，限流

### 查看健康状态

```bash
docker inspect --format='{{.State.Health.Status}}' <container>
docker inspect <container> | grep -A20 Health
```

### 查看日志

```bash
docker compose logs -f app
docker compose logs --tail=200 app
```

日志轮转已限制总量 ~30MB，无需手动清理。

## 常见问题

### 容器反复重启（Restarting）

1. `docker compose logs app` 看退出原因
2. 若 `Permission denied` 绑定端口 → `PORT` 设了 <1024，改回 ≥1024 或用反代
3. 若 QQ 音乐 API 整体不可达 → 服务依赖外网，检查宿主网络/出口

### healthcheck 一直 unhealthy

1. 确认容器内 `python` 可用：`docker compose exec app python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/api/health').close()"`
2. 确认 `PORT` 环境变量与 uvicorn 实际监听端口一致
3. 看 `docker compose logs` 是否有启动报错（start_period 仅 10s，慢机器冷启动可能不够）

### 限流误伤全局

直连部署开箱即用。若在前面加了 nginx 反代，**必须**配置：

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

否则限流按代理 IP 计数，所有用户共享一个配额，10/minute 会瞬间打满。

### 解析数量少于总数

正常现象：个别歌曲下架/区域限制会被跳过。响应中 `total_count`（QQ 音乐原始总数）与 `songs_count`（实际解析数）的差值即缺失数。若差距过大（如少几十首以上），可能是 QQ 音乐接口限流，过段时间重试。

## 回滚

无状态服务，回滚即重新部署旧镜像：

```bash
# 回到上一个镜像
docker compose down
docker tag <previous-image> qqplaylist-export:rollback
# 或直接 git checkout <旧 commit> && docker compose up -d --build
```

无数据迁移 concerns，新旧版本可随时切换。

## 信号与优雅关闭

`init: true` 让 tini 做 PID 1，转发 SIGTERM 给 uvicorn。`docker compose stop` 会触发 graceful shutdown，默认 10s 超时后 SIGKILL。无在途状态需持久化，硬停也无数据丢失。
