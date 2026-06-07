import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database import init_db
from routes.chat import router as chat_router
from routes.admin import router as admin_router
from rag.ingest import ingest_default_faqs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ingest_default_faqs()
    yield


app = FastAPI(
    title="Customer Support Chatbot API",
    description="RAG-powered AI customer support — Basic tier",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static widget files served at /widget ─────────────────────────
WIDGET_DIR = os.path.join(os.path.dirname(__file__), "widget")
app.mount("/widget", StaticFiles(directory=WIDGET_DIR, html=True), name="widget")

# ── Routes — Basic ────────────────────────────────────────────────
app.include_router(chat_router,  prefix="/api/chat",  tags=["Chat"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])


@app.get("/api/config")
async def get_config():
    return {
        "companyName": os.getenv("COMPANY_NAME", "Support"),
        "welcomeMessage": os.getenv("WELCOME_MESSAGE", "👋 Hi there! How can I help?"),
        "accentColor": os.getenv("ACCENT_COLOR", "#6C63FF"),
    }

@app.get("/")
async def root():
    return {"status": "ok", "tier": "basic", "widget_url": "/widget/widget.html"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
