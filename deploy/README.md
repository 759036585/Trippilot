# 部署说明

流水线在 [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)：推送 `main` 后自动构建前端、检查后端，然后通过 SSH 同步到云服务器并重启服务。

```
push main
   ↓
build（GitHub 跑）：npm ci → vue-tsc + vite build → pip install → compileall
   ↓
deploy（GitHub 跑）：rsync 源码 + dist → 服务器，pip install → systemctl restart → 健康检查 → nginx reload
   ↓
nginx:  / → /opt/trippilot/trippilot-frontend/dist
        /api/ → 127.0.0.1:8000
```

服务器上不需要装 Node，前端产物在 GitHub 上构建好再传过去；也不需要把仓库 clone 到服务器，代码由 rsync 同步。

---

## 一、服务器准备（只做一次）

以 Ubuntu / Debian 为例。

### 1. 创建部署用户和目录

```bash
sudo adduser trippilot
sudo mkdir -p /opt/trippilot
sudo chown -R trippilot:trippilot /opt/trippilot
```

`APP_DIR` 就是 `/opt/trippilot`，后端在 `/opt/trippilot/trippilot-backend`，前端产物在 `/opt/trippilot/trippilot-frontend/dist`。

### 2. 安装运行环境

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx curl
# PostgreSQL：如果还没装
sudo apt install -y postgresql
sudo -u postgres psql -c "CREATE DATABASE trippilot_db;"
```

### 3. 配置后端环境变量

```bash
sudo -u trippilot mkdir -p /opt/trippilot/trippilot-backend
sudo -u trippilot cp /opt/trippilot/trippilot-backend/.env.example /opt/trippilot/trippilot-backend/.env.local
sudo -u trippilot nano /opt/trippilot/trippilot-backend/.env.local
```

按模板填好数据库、高德、大模型和 `AUTH_SECRET`。

> ⚠️ 这个文件**不在 git 里，也不会被部署覆盖**（rsync 排除了 `.env.local`），但首次部署要求它已存在，否则流水线会直接报错退出。
>
> 如果第一次部署前目录里还没有 `.env.example`，可以先本地 `scp` 一个上去，或者手写一份。

### 4. 安装 systemd 服务

```bash
sudo cp /opt/trippilot/deploy/trippilot.service /etc/systemd/system/trippilot.service
# 如果部署用户不是 trippilot，或路径不是 /opt/trippilot，先改这两行：User= / WorkingDirectory= / ExecStart=
sudo systemctl daemon-reload
sudo systemctl enable trippilot
```

### 5. 配置 sudo 免密（流水线需要）

```bash
sudo visudo -f /etc/sudoers.d/trippilot-deploy
```

写入（路径按 `which systemctl` / `which nginx` 的实际结果调整）：

```
trippilot ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart trippilot, /usr/bin/systemctl reload nginx, /usr/sbin/nginx -t, /usr/bin/journalctl -u trippilot *
```

### 6. 配置 nginx

```bash
sudo cp /opt/trippilot/deploy/nginx.conf /etc/nginx/sites-available/trippilot
sudo ln -sf /etc/nginx/sites-available/trippilot /etc/nginx/sites-enabled/trippilot
sudo rm -f /etc/nginx/sites-enabled/default
# 把 server_name 改成你的域名或公网 IP
sudo nano /etc/nginx/sites-available/trippilot
sudo nginx -t && sudo systemctl reload nginx
```

需要 HTTPS 的话再执行 `sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d 你的域名`。

### 7. 生成部署密钥

在**本地**执行：

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

- `deploy_key`（私钥）→ 填到 GitHub secret `SSH_PRIVATE_KEY`
- `deploy_key.pub`（公钥）→ 追加到服务器的 `/home/trippilot/.ssh/authorized_keys`

```bash
ssh-copy-id -i deploy_key.pub trippilot@你的服务器IP
# 或者手动：
# cat deploy_key.pub | ssh trippilot@服务器IP 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

验证：`ssh -i deploy_key trippilot@服务器IP 'echo ok'`。密钥用完就删掉本地文件，别提交到仓库。

---

## 二、GitHub 仓库配置

`Settings → Secrets and variables → Actions`：

### Secrets

| 名称 | 说明 |
|---|---|
| `SSH_PRIVATE_KEY` | 上一步生成的部署私钥**全文**（含 `-----BEGIN...` 和结尾换行） |
| `SERVER_HOST` | 服务器 IP 或域名 |
| `SERVER_USER` | `trippilot` |
| `APP_DIR` | `/opt/trippilot` |
| `SERVER_PORT` | 可选，默认 `22` |
| `VITE_AMAP_JS_KEY` | 高德 **Web 端 (JS API)** Key，会打进前端产物 |
| `VITE_AMAP_SECURITY_CODE` | 与上面配对的安控密钥 |

### Variables（可选）

| 名称 | 说明 |
|---|---|
| `VITE_API_BASE_URL` | 不配或留空 = 同源部署（nginx 反代 `/api`，推荐）。只有前后端分开部署时才填后端公网地址，例如 `https://api.example.com` |

> 注意前后端的高德 Key 类型不同：`VITE_AMAP_JS_KEY` 是 JS API Key，后端的 `AMAP_API_KEY` 是 Web 服务 Key，要分别申请。

---

## 三、首次部署

推送任何提交到 `main`，或到 `Actions → Deploy → Run workflow` 手动触发。

第一次会：

1. 检查 secrets 是否齐全（缺了会明确报出缺哪个）
2. 在 GitHub 上构建前端
3. rsync 同步代码（跳过 `venv/`、`node_modules/`、`.env.local`）
4. 服务器端创建 venv、装依赖
5. `systemctl restart trippilot`，轮询 `http://127.0.0.1:8000/` 做健康检查
6. `nginx -t && systemctl reload nginx`

打开 `http://你的域名` 应该能看到首页。

---

## 四、排查

| 现象 | 处理 |
|---|---|
| `Permission denied (publickey)` | 公钥没加到 `~/.ssh/authorized_keys`，或 `SERVER_USER` 不对 |
| `sudo: a password is required` | `/etc/sudoers.d/trippilot-deploy` 没配对，注意命令必须写绝对路径且参数完全一致 |
| 健康检查失败 | 流水线会打印 `journalctl -u trippilot -n 50`；本地对照 `sudo -u trippilot /opt/trippilot/trippilot-backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000` 看报错 |
| 页面能开但接口 502 | 后端没起；`systemctl status trippilot`、`journalctl -u trippilot -f` |
| 地图不显示、控制台报 `INVALID_USER_SCODE` | `VITE_AMAP_SECURITY_CODE` 没配或和高德控制台的 Key 不配对 |
| 刷新 `/trips` 变 404 | nginx 少了 `try_files $uri $uri/ /index.html`，检查 `deploy/nginx.conf` 是否覆盖到 |

回滚：`git revert <提交>` 后推送到 `main`，流水线会重新部署回上一个版本。

> 流水线只会同步代码和前端产物，**不会改动 `/etc/nginx/` 和 `/etc/systemd/system/` 下的文件**。改了 `deploy/nginx.conf` 或 `deploy/trippilot.service` 之后，需要手动重新 `cp` 到系统目录并 reload。这样设计是为了避免自动部署误改线上服务器配置。

---

## 五、本地预览构建产物

```bash
cd trippilot-frontend
npm run build
npm run preview
```
