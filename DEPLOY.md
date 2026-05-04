# Deploy

## 环境变量

### 后端

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | 是 | - | DeepSeek API Key，用于翻译 |
| `ADMIN_API_KEY` | 否 | 空 | 管理接口鉴权 Key，留空则管理接口不可用 |
| `REDDIT_CLIENT_ID` | 否 | 空 | Reddit OAuth2 Client ID |
| `REDDIT_CLIENT_SECRET` | 否 | 空 | Reddit OAuth2 Client Secret |
| `REDDIT_USER_AGENT` | 否 | `acgfeed/1.0` | Reddit API User-Agent |
| `DATABASE_PATH` | 否 | `./data/acgfeed.db` | SQLite 数据库路径 |
| `FRONTEND_URL` | 否 | `http://localhost:3000` | 前端地址，用于 CORS |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `RETENTION_DAYS` | 否 | `7` | 数据保留天数 |
| `FETCH_INTERVAL_MINUTES` | 否 | `30` | 自动抓取间隔（分钟） |

### 前端

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `NEXT_PUBLIC_API_URL` | 否 | `http://localhost:8000` | 浏览器访问的后端 API 地址 |

### 说明

- 只有 `DEEPSEEK_API_KEY` 是必填的，其他均有默认值。
- 如需 Reddit 数据源，需同时配置 `REDDIT_CLIENT_ID` 和 `REDDIT_CLIENT_SECRET`。
- `ADMIN_API_KEY` 用于保护 `POST /api/admin/*` 接口，如果不配置则管理接口拒绝所有请求。
- 生产部署时 `NEXT_PUBLIC_API_URL` 应设为后端的公网地址（如 `https://api.example.com`），`FRONTEND_URL` 应设为前端公网地址。

---

## 手动部署

### 1. 准备运行环境

- 安装 Python 3.12 或更高版本。
- 安装 Node.js 20 或更高版本。
- 无需额外数据库，后端使用 SQLite 自动创建。

### 2. 后端部署

进入后端目录：

```bash
cd /path/to/acghacknews/backend
```

创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

在 `backend/` 目录创建 `.env` 或 `.env.local`：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key
ADMIN_API_KEY=your-admin-api-key
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=acgfeed/1.0
DATABASE_PATH=./data/acgfeed.db
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
RETENTION_DAYS=7
FETCH_INTERVAL_MINUTES=30
```

启动 FastAPI：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果要直接对公网监听：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 前端部署

进入前端目录：

```bash
cd /path/to/acghacknews/frontend
```

安装依赖：

```bash
npm install
```

在 `frontend/` 目录创建 `.env.local`：

```env
NEXT_PUBLIC_API_URL=https://api.example.com
```

本地开发时：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

构建前端：

```bash
npm run build
```

启动生产服务：

```bash
npm run start -- --hostname 127.0.0.1 --port 3000
```

如果要直接对公网监听：

```bash
npm run start -- --hostname 0.0.0.0 --port 3000
```

### 4. 反向代理

推荐使用 Nginx 或 Caddy：

- `https://your-site.example.com` -> `http://127.0.0.1:3000`
- `https://api.example.com` -> `http://127.0.0.1:8000`

Nginx 配置示例：

```nginx
# 前端
server {
    listen 443 ssl http2;
    server_name your-site.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 后端 API
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. 基本启动顺序

1. 先启动后端 API
2. 确认 `http://127.0.0.1:8000/docs` 可访问（FastAPI 自动文档）
3. 确认 `http://127.0.0.1:8000/api/health` 返回 `{"status": "ok"}`
4. 再构建并启动前端
5. 最后接入反向代理和域名

### 6. 手动验证

后端验证：

```bash
# 健康检查
curl http://127.0.0.1:8000/api/health

# 获取信息流
curl http://127.0.0.1:8000/api/feed

# 手动触发抓取（需要 ADMIN_API_KEY）
curl -X POST http://127.0.0.1:8000/api/admin/trigger-fetch \
  -H "X-Admin-Key: your-admin-api-key"

# 手动插入数据
curl -X POST http://127.0.0.1:8000/api/admin/items \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-api-key" \
  -d '{
    "items": [{
      "source": "reddit",
      "source_url": "https://reddit.com/r/anime/comments/xxx",
      "original_title": "Test Post",
      "translated_title": "测试帖子"
    }]
  }'
```

前端验证：

```bash
curl http://127.0.0.1:3000/
```

浏览器验证：

- 打开首页，确认信息流能显示
- 切换语言（中/EN），确认标题和内容正确切换
- 切换数据源筛选，确认结果正确
- 切换排序（Hot/New），确认排序生效

### 7. systemd 服务配置

后端服务：

```ini
[Unit]
Description=ACG HackNews Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/www/acghacknews/backend
EnvironmentFile=/www/acghacknews/backend/.env.local
ExecStart=/www/acghacknews/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 5003
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

保存为 `/etc/systemd/system/acghacknews-backend.service`

```bash
# 创建数据目录
sudo mkdir -p /www/acghacknews/backend/data
sudo chown -R www-data:www-data /www/acghacknews/backend/data

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable acghacknews-backend
sudo systemctl start acghacknews-backend
sudo systemctl status acghacknews-backend
```

前端服务（pm2）：

```bash
pm2 start npm --name "acghacknews-frontend" -- start -- --hostname 0.0.0.0 --port 5004
```

### 8. 更新部署

```bash
cd /www/acghacknews
git pull

# 后端
cd /www/acghacknews/backend
source .venv/bin/activate
pip install -e .
sudo systemctl restart acghacknews-backend

# 前端
cd /www/acghacknews/frontend
npm install
npm run build
pm2 restart acghacknews-frontend
```

查看日志：

```bash
# 后端日志
journalctl -u acghacknews-backend -n 100 --no-pager
journalctl -u acghacknews-backend -f

# 前端日志
pm2 logs acghacknews-frontend
```

### 9. 生产建议

- 后端和前端都建议交给 systemd 或 pm2 守护，不要手工挂前台。
- `NEXT_PUBLIC_API_URL` 应填浏览器真实访问到的后端公网地址。
- `FRONTEND_URL` 应填前端公网地址，用于 CORS 白名单。
- 不要把 `DEEPSEEK_API_KEY` 和 `ADMIN_API_KEY` 暴露到前端公开环境变量。
- 后端 SQLite 数据库文件默认在 `data/acgfeed.db`，建议定期备份。
- 默认每 30 分钟自动抓取一次数据，可通过 `FETCH_INTERVAL_MINUTES` 调整。
- 默认保留 7 天数据，可通过 `RETENTION_DAYS` 调整。
