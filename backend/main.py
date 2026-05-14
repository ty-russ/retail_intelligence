from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import analytics, insights

app = FastAPI(
    title="Retail Insight Cancellation Intelligence API",
    description="Analytics pipeline and AI insights for order cancellation analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)
app.include_router(insights.router)


@app.get("/")
def root():
    return {
        "service": "Retail Insight Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "analytics": "/api/analytics/",
            "insights":  "/api/insights/",
        }
    }


@app.get("/health")
def health():
    return {"status": "ok"}
