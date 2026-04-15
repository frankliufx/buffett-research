"""FastAPI 服务入口

运行: uvicorn api.main:app --port 8502 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import stock, analysis, hedge_fund

app = FastAPI(title="Buffett Research API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock.router,      prefix="/api/stock",      tags=["stock"])
app.include_router(analysis.router,   prefix="/api/analysis",   tags=["analysis"])
app.include_router(hedge_fund.router, prefix="/api/hedge-fund", tags=["hedge-fund"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
