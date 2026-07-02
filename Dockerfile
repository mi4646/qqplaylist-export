# ---- 前端构建 ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci
COPY frontend/ ./
RUN npm run build

# ---- 后端运行 ----
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV HOST=0.0.0.0 \
    PORT=8081
EXPOSE ${PORT}
# ponytail: exec form 不展开环境变量，用 sh -c 让 ${VAR} 生效；exec 让 uvicorn 接管 PID 1 接收 SIGTERM
CMD ["sh", "-c", "exec uvicorn app.main:app --host ${HOST} --port ${PORT}"]
