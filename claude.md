# Phase 1 — Project Scaffold & Config

Goal: `uvicorn app.main:app --reload` starts, and `GET /health` returns 200.

Create these files in this order.

---

## 1. Folder setup

```bash
mkdir -p erp-analytics/app/services/transformers
mkdir -p erp-analytics/app/analytics
mkdir -p erp-analytics/app/routers
mkdir -p erp-analytics/app/utils
mkdir -p erp-analytics/tests
mkdir -p erp-analytics/data/samples
mkdir -p erp-analytics/data/temp
cd erp-analytics
touch app/__init__.py app/services/__init__.py app/services/transformers/__init__.py
touch app/analytics/__init__.py app/routers/__init__.py app/utils/__init__.py
```

The `__init__.py` files are empty — they just tell Python "this folder is a package" so you can do `from app.services import file_reader` later.

---

## 2. `requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
pydantic-settings==2.2.1
pandas==2.2.2
openpyxl==3.1.2
xlrd==2.0.1
pyspark==3.5.1
pyarrow==16.0.0
rapidfuzz==3.9.0
python-magic==0.4.27
python-dotenv==1.0.1
```

## 3. `requirements-dev.txt`

```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

Install both:
```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 4. `.env.example`

Copy this to `.env` and adjust as needed. `pydantic-settings` reads `.env` automatically.

```
APP_ENV=development
MAX_UPLOAD_SIZE_MB=100
ALLOWED_EXTENSIONS=csv,xlsx
SPARK_MASTER=local[*]
SPARK_EXECUTOR_MEMORY=2g
SPARK_SHUFFLE_PARTITIONS=8
TEMP_DIR=./data/temp
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## 5. `app/config.py`

This is the ONLY place environment variables get read. Everything else imports `settings` from here — never call `os.environ` anywhere else in the app.

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = "csv,xlsx"  # comma-separated, parsed below

    # Spark
    SPARK_MASTER: str = "local[*]"
    SPARK_EXECUTOR_MEMORY: str = "2g"
    SPARK_SHUFFLE_PARTITIONS: int = 8

    # Filesystem
    TEMP_DIR: str = "./data/temp"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached so we parse .env once, not on every import."""
    return Settings()


settings = get_settings()
```

**Why `@lru_cache`?** Without it, every module that does `from app.config import settings`
would re-read and re-parse `.env`. `lru_cache` makes `get_settings()` a singleton factory —
first call does the work, every call after returns the same cached object.

---

## 6. `app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.spark_session import spark_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    spark_manager.initialize(settings)
    yield
    # --- shutdown ---
    spark_manager.stop()


app = FastAPI(title="ERP Analytics Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    spark_status = "ready" if spark_manager.is_ready() else "not_ready"
    return {"status": "ok", "spark": spark_status}
```

Notice `main.py` imports `spark_manager` from `app/services/spark_session.py` — a file
we haven't built yet (that's Phase 5 in the plan). For Phase 1's milestone check, use
this **stub** version instead so you can run the app right now without Spark installed
correctly yet:

### Temporary stub — `app/services/spark_session.py`

```python
class SparkSessionManager:
    """Placeholder for Phase 1. Real implementation comes in Phase 5."""

    def __init__(self):
        self._ready = False

    def initialize(self, settings):
        self._ready = True  # pretend Spark started

    def stop(self):
        self._ready = False

    def is_ready(self) -> bool:
        return self._ready


spark_manager = SparkSessionManager()
```

You'll replace this whole file in Phase 5 with a real `SparkSession` — but keeping the
same class name and method signatures (`initialize`, `stop`, `is_ready`) means `main.py`
never has to change.

---

## Milestone check

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

Expected:
```json
{"status": "ok", "spark": "ready"}
```

If you get that, Phase 1 is done — config loads, the app starts, the lifespan handler
fires on startup, and `/health` reflects it.

---

## What to type next

Say "next phase" and I'll give you Phase 2 (file validation: `exceptions.py` +
`validators.py`), same format — code plus the reasoning behind each design choice.