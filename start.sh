#!/bin/zsh
cd /Users/frankliu/stock-analyst

# 加载环境变量
[ -f .env ] && export $(grep -v '^#' .env | xargs)

# 启动 FastAPI (port 8502)
echo "Starting FastAPI on :8502..."
.venv/bin/uvicorn api.main:app --port 8502 --log-level warning &
API_PID=$!

# 启动 Streamlit (port 8501)
echo "Starting Streamlit on :8501..."
.venv/bin/streamlit run app.py --server.port 8501 &
ST_PID=$!

echo ""
echo "  Streamlit  → http://localhost:8501"
echo "  API Docs   → http://localhost:8502/docs"
echo ""
echo "Press Ctrl+C to stop both"

trap "kill $API_PID $ST_PID 2>/dev/null; exit" INT TERM
wait
