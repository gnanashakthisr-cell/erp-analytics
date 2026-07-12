from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.analyze import router as analyze_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="ERP Analytics Platform", lifespan=lifespan)

app.include_router(analyze_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
