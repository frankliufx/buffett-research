# Streamlit Cloud 部署指引

> 本仓库已为 Streamlit Community Cloud 部署做好准备。
> 仓库：`frankliufx/buffett-research`（main 分支）

---

## ✅ 部署前已就绪项

- `app.py` — Streamlit 主入口
- `requirements.txt` — 完整依赖（含 streamlit, yfinance, anthropic, plotly 等）
- `.streamlit/config.toml` — Blackstone 暗色金色主题
- `.streamlit/secrets.toml.example` — secrets 模板
- `.gitignore` — 已排除 `.env / config.yaml / users.yaml / secrets.toml`

---

## 🚀 部署步骤（约 5 分钟）

### 1. 登录 Streamlit Cloud
打开 https://share.streamlit.io/ → 用 GitHub 账号登录

### 2. 创建新 App
点击 **New app**，配置：
- **Repository**: `frankliufx/buffett-research`
- **Branch**: `main`
- **Main file path**: `app.py`
- **App URL**: 自定义（例如 `buffett-research-frank`）

### 3. 配置 Secrets（关键步骤）

进入 **Advanced settings → Secrets**，粘贴：

```toml
# 至少需要一个 API Key
OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx"

# 可选
# ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx"
# DEEPSEEK_API_KEY  = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

> 你的 OpenRouter Key 在本地 `~/stock-analyst/.env` 中，**不要复制 .env 文件**，只复制 Key 值粘到上面的模板里。

### 4. 点击 **Deploy**
首次构建约 3-5 分钟（pip install 依赖）。

---

## 🔧 部署后检查

打开公网 URL 后验证以下功能：

- [ ] 首页 Blackstone 暗色金色主题正常加载
- [ ] 美股 / 港股 / A股 三市场行情可拉取
- [ ] 巴菲特指标三市场仪表盘正常
- [ ] 选某只股票 → 主分析页 → MOAT 五维度评分
- [ ] AI Advisor 对话页能调通 OpenRouter
- [ ] 财务/技术分析图表渲染

---

## 🚨 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| `urllib3` 兼容性错 | LibreSSL vs urllib3 v2 | requirements 已固定 `urllib3>=1.26,<3` |
| AI 调用 401 | secrets 没配 | 回到 Settings → Secrets 检查 Key |
| 首屏白屏 | 依赖装失败 | 看 Cloud 日志 → manage app → Logs |
| 美股数据空 | 东方财富 API 限速 | 等几分钟重试 |

---

## 📝 后续维护

- 改代码 → push 到 main → Streamlit Cloud 自动重新部署
- 改 Secrets → Settings → Secrets → Save → 自动重启
- 看日志 → Cloud 后台 → Manage App → Logs

---

## 💡 进阶（可选）

- **绑定自定义域名**: Streamlit Cloud 免费版支持 `*.streamlit.app`，自定义域名需付费
- **数据缓存**: 已用 `@st.cache_data` 缓存 5 分钟，减少 API 调用
- **多用户认证**: `users.yaml` 已支持，需要时启用 src/auth.py
