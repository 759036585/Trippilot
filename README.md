# TripPilot 旅程 AI

用大模型自动规划旅行行程的 Web 应用：输入目的地、日期、预算和偏好，AI 会调用高德地图的真实数据查询景点与路线，生成可直接执行的行程，并在地图上串成一条路线。

## 功能

- **AI 行程规划**：通过 function calling 让模型自己查询景点、估算交通耗时，最后结构化提交行程
- **地图工作台**：左侧按天列出行程，点击定位到地图；右侧展示真实道路折线
- **出行方式切换**：打车 / 公交地铁 / 步行三种方案，公交方案可展开查看具体坐哪条线、换乘几次、步行到哪个站
- **周边推荐**：以任意行程点为中心，搜索附近的景点、美食、酒店、购物
- **账号与历史**：注册 / 登录后行程自动保存，可随时回看并用密码继续编辑
- **游客模式**：不登录也能规划，只是不会保存

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus + 高德 JS API 2.0 |
| 后端 | FastAPI + SQLAlchemy + PostgreSQL + Pydantic Settings |
| AI | DeepSeek（OpenAI 兼容协议）function calling |
| 地图服务 | 高德地图 Web 服务 API |

## 目录结构

```
trippilot/
├── trippilot-backend/     # FastAPI 后端
│   ├── main.py            # 接口入口
│   ├── config.py          # 环境变量加载
│   ├── database/          # ORM 模型与会话
│   └── services/          # agent / amap / auth
└── trippilot-frontend/    # Vue 3 前端
    └── src/
        ├── views/         # Home / CreateTrip / MyTrips / Login
        │   └── workbench/ # 行程工作台：页面 + 子组件 + composables
        ├── components/    # AppHeader 等
        ├── api/           # axios 封装
        └── stores/        # Pinia（用户登录态）
```

## 本地启动

### 1. 环境变量

两个子项目都从 `.env.local` 读取真实配置，模板文件已提交：

```bash
# 后端
cd trippilot-backend
cp .env.example .env.local     # Windows: Copy-Item .env.example .env.local

# 前端
cd trippilot-frontend
cp .env.example .env.local
```

按模板里的注释填入数据库连接串、高德 Key、大模型 Key 和 token 签名密钥。

> `.env.local` 已在 `.gitignore` 中排除，不会进入版本库，请勿强行提交。

### 2. 后端

```bash
cd trippilot-backend
python -m venv venv
venv\Scripts\activate          # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. 前端

```bash
cd trippilot-frontend
npm install
npm run dev
```

打开 http://localhost:5173 即可。修改 `.env.local` 后需要重启 `npm run dev` 才会生效。

## 部署

推送到 `main` 会触发 [GitHub Actions](.github/workflows/deploy.yml)：构建前端 → 检查后端 → tar over ssh 同步到云服务器 → 重启 uvicorn → 重载 nginx。

服务器准备、Secrets 配置和排错见 [deploy/README.md](deploy/README.md)，配套文件在 [deploy/](deploy/)（systemd 服务与 nginx 站点配置）。

## 配置说明

后端需要以下变量：

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接串，格式 `postgresql+psycopg://用户:密码@主机:端口/库名` |
| `AMAP_API_KEY` | 高德「Web 服务」类型 Key |
| `LLM_API_KEY` / `LLM_BASE_URL` | 大模型接口地址与密钥 |
| `AUTH_SECRET` | 登录 token 签名密钥，建议用 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成 |

前端需要：

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE_URL` | 后端地址，默认 `http://127.0.0.1:8000` |
| `VITE_AMAP_JS_KEY` | 高德「Web 端 (JS API)」Key |
| `VITE_AMAP_SECURITY_CODE` | 与 JS API Key 配套的安全密钥 |

注意前后端的高德 Key 类型不同，需要在高德控制台分别创建，不能混用。`VITE_` 前缀的变量会被打包进前端产物，只适合放这类公开 Key。
