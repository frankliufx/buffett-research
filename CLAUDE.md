# CLAUDE.md — Stock Analyst（巴菲特投研系统）

## 项目身份
**Frank 的核心 P0 项目** — 巴菲特投研系统（Streamlit + 10 页面）。
GitHub: `frankliufx/buffett-research`
下一步：部署到 Streamlit Cloud（见 `docs/DEPLOY_STREAMLIT_CLOUD.md`）

## Tech Stack
- **Framework**: Streamlit + Python
- **数据**: pandas / numpy
- **架构**: src/committee, src/hedge_fund (agents 系统)

## Recommended Claude Code Skills
**优先调用**:
- `python-patterns` `python-testing`
- `deep-research` `market-research`
- `dashboard-builder` `content-engine`
- `pytorch-patterns`（如涉及 ML 模型）

**缺失（待新建）**: `streamlit-patterns`

**优先 Sub-agents**:
- `python-reviewer` 代码改动后必用
- `stock-research-agent` 投资分析（已可用）
- `research-agent` 行业/宏观研究
- `performance-optimizer` 慢查询/慢渲染

**Slash Commands**: `/feature-dev` `/python-review` `/tdd`

## 禁用 / 忽略的 Skills
- 所有非 Python 语言生态
- 行业垂直（healthcare/logistics/energy/Web3）
- 移动端

## 工作规范
继承 `~/.claude/rules/common/`。特别强调：
- **金融数据准确性 > 速度** — 关键计算必须有 unit test
- **API key 严禁硬编码** — `.env` + `.env.example`
- **Streamlit 状态管理** — 谨慎使用 `st.session_state`

## 当前状态
合并完成，准备部署。
