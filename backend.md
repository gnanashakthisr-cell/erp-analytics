# ERP Analytics Platform — Backend Build Plan

> Build a clean, testable backend first. No frontend. No premature optimization.
> Get one module (Sales) working end-to-end before touching Inventory or Purchases.

---

## Guiding Principles

- **One working thing beats three half-built things** — finish Sales fully before copying the pattern
- **Test as you build** — not after; catch bugs at the layer they live in
- **Pandas reads, Spark transforms** — never blur this boundary
- **One SparkSession, always** — initialized at startup, never per request
- **Fail fast and clearly** — bad files and bad mappings return structured errors immediately

---

## Project Structure

```
erp-analytics/
├── app/
│   ├── main.py                          # FastAPI app, lifespan handlers, CORS, health
│   ├── config.py                        # All settings via pydantic-settings
│   ├── services/
│   │   ├── spark_session.py             # Singleton SparkSession manager
│   │   ├── file_reader.py               # Pandas CSV/XLSX reader
│   │   ├── column_mapper.py             # RapidFuzz auto-mapping engine
│   │   ├── df_converter.py              # Pandas → Spark bridge
│   │   └── transformers/
│   │       ├── base.py                  # Abstract BaseTransformer
│   │       ├── sales.py
│   │       ├── inventory.py
│   │       └── purchases.py
│   ├── analytics/
│   │   ├── sales.py                     # Sales KPI functions
│   │   ├── inventory.py
│   │   └── purchases.py
│   ├── routers/
│   │   └── analyze.py                   # POST /analyze/sales|inventory|purchases
│   └── utils/
│       ├── exceptions.py                # Custom exception hierarchy
│       └── validators.py                # File size, extension, MIME checks
├── tests/
│   ├── conftest.py                      # Shared fixtures
│   ├── test_file_reader.py
│   ├── test_column_mapper.py
│   ├── test_transformers.py
│   └── test_endpoints.py
├── data/
│   └── samples/                         # Put real messy ERP exports here
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Phase 1 — Project Scaffold & Config

**Goal:** Runnable FastAPI app with a working `/health` endpoint.

### Step 1 — `requirements.txt`

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

### Step 2 — `requirements-dev.txt`

```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

### Step 3 — `app/config.py`

Settings to include:
- `APP_ENV` (development / production)
- `MAX_UPLOAD_SIZE_MB` (default 100)
- `ALLOWED_EXTENSIONS` (csv, xlsx)
- `SPARK_MASTER` (local[*])
- `SPARK_EXECUTOR_MEMORY` (2g)
- `SPARK_SHUFFLE_PARTITIONS` (8)
- `TEMP_DIR` (./data/temp)
- `LOG_LEVEL` (INFO)
- `CORS_ORIGINS` (list)

### Step 4 — `app/main.py`

- `lifespan` handler: start SparkSession on startup, stop on shutdown
- CORS middleware
- Include analyze router
- `GET /health` → `{"status": "ok", "spark": "ready"}`

**Milestone check:** `uvicorn app.main:app --reload` starts, `/health` returns 200.

---

## Phase 2 — File Intake & Validation

**Goal:** Accept a file upload, validate it, reject bad files with clear errors.

### Step 5 — `app/utils/exceptions.py`

Custom exception classes:
```
FileTooLargeError        → 413
UnsupportedFormatError   → 415
EmptyFileError           → 400
CorruptFileError         → 422
MappingCoverageError     → 422
ProcessingError          → 500
```

Each exception returns a structured JSON response:
```json
{
  "error": "FileTooLargeError",
  "message": "File exceeds 100MB limit. Received: 143MB",
  "detail": {}
}
```

### Step 6 — `app/utils/validators.py`

`FileValidator` class with these checks in order:
1. File size ≤ MAX_UPLOAD_SIZE_MB
2. Extension in allowed list
3. MIME type matches extension (python-magic)
4. File is not empty (0 bytes)

**Milestone check:** Upload a 200MB file → get `FileTooLargeError`. Upload a `.exe` → get `UnsupportedFormatError`.

---

## Phase 3 — Pandas Ingestion Layer

**Goal:** Read any valid CSV or XLSX into a clean Pandas DataFrame with metadata.

### Step 7 — `app/services/file_reader.py`

`FileReadResult` dataclass:
```python
@dataclass
class FileReadResult:
    df: pd.DataFrame
    filename: str
    columns: list[str]
    row_count: int
    preview: list[dict]       # first 10 rows
    null_stats: dict          # null % per column
    warnings: list[str]       # non-fatal issues found
```

`FileReader` class:

- `read(file_path, filename) → FileReadResult`
- CSV: try `utf-8` → `latin-1` → `cp1252` → `chardet` fallback; auto-detect delimiter
- XLSX: use `openpyxl`; XLS: use `xlrd`
- Strip leading/trailing whitespace from all column names
- Catch `BadZipFile`, `ParserError`, `EmptyDataError` → raise `CorruptFileError`
- Compute null percentage per column
- Warn (don't crash) if >50% of any column is null

**Milestone check:** Feed it a messy CSV with mixed encodings → get back a clean DataFrame and accurate null stats.

---

## Phase 4 — Column Mapping Layer

**Goal:** Automatically map uploaded column names to standard ERP schema fields.

### Step 8 — Standard Schema Definitions (inside `column_mapper.py`)

**Sales standard fields:**
```
invoice_id, invoice_date, customer_id, customer_name,
product_id, product_name, quantity, unit_price, total_amount,
branch, currency
```

**Inventory standard fields:**
```
product_id, product_name, category, stock_quantity,
unit, warehouse, last_updated
```

**Purchases standard fields:**
```
purchase_id, purchase_date, supplier_id, supplier_name,
product_id, product_name, quantity, unit_cost, total_cost, currency
```

### Step 9 — `app/services/column_mapper.py`

`MappingResult` dataclass:
```python
@dataclass
class MappingResult:
    mapping: dict[str, str]        # { "Invoice No": "invoice_id" }
    confidence: dict[str, float]   # { "invoice_id": 0.94 }
    unmapped_source: list[str]     # columns with no match
    unmapped_target: list[str]     # required fields not covered
    coverage: float                # % of required fields mapped
```

`ColumnMapper` class:
- `map_columns(df_columns, module) → MappingResult`
- Use RapidFuzz `process.extractOne` with a threshold of 70
- Define alias dictionaries per field (e.g. `invoice_id` matches: `invoice no`, `inv no`, `bill no`, `voucher no`)
- Raise `MappingCoverageError` if required fields coverage < 80%

**Milestone check:** Pass in `["Invoice No", "Qty Sold", "Rate", "Amount", "Date"]` for sales → get back a confident mapping.

---

## Phase 5 — SparkSession Manager

**Goal:** One shared SparkSession available across the entire app.

### Step 10 — `app/services/spark_session.py`

`SparkSessionManager` class:
- `initialize(config)` — called once in FastAPI lifespan startup
- `get() → SparkSession` — returns the existing session; raises if not initialized
- `stop()` — called in lifespan shutdown
- Config pulled from `app/config.py`: master, memory, shuffle partitions, temp dir
- Set `spark.sql.session.timeZone` to UTC
- Set log level to ERROR (suppress Spark noise)
- Windows support: check for `HADOOP_HOME`; log a clear warning if missing

**Milestone check:** App starts → Spark initializes → `/health` returns `{"spark": "ready"}`. App stops → Spark shuts down cleanly.

---

## Phase 6 — Pandas → Spark Conversion Layer

**Goal:** Reliably convert a mapped Pandas DataFrame into a typed Spark DataFrame.

### Step 11 — `app/services/df_converter.py`

`ConversionResult` dataclass:
```python
@dataclass
class ConversionResult:
    spark_df: DataFrame
    total_rows: int
    converted_rows: int
    rejected_rows: int
    rejection_reasons: list[str]
```

`DataFrameConverter` class:
- `convert(pandas_df, mapping, module) → ConversionResult`
- Apply column mapping (rename columns)
- Add missing optional columns as nulls
- Cast types explicitly:
  - date columns → `DateType()` with multiple format attempts
  - numeric columns → `DoubleType()` with coercion (bad rows flagged, not crashed)
  - string columns → `StringType()` with `.strip()`
- Track rows that fail type coercion → `rejected_rows`
- Add `upload_batch_id` column

**Milestone check:** Pass in a messy Pandas DataFrame with mixed date formats → get a clean Spark DataFrame with correctly typed columns and a count of rejected rows.

---

## Phase 7 — Transformer Layer

**Goal:** Apply business-level cleaning and validation on top of the converted Spark DataFrame.

### Step 12 — `app/services/transformers/base.py`

`TransformResult` dataclass:
```python
@dataclass
class TransformResult:
    df: DataFrame
    uploaded_rows: int
    processed_rows: int
    dropped_rows: int
    duplicate_rows: int
    quality_metrics: dict
```

`BaseTransformer` abstract class:
- `transform(spark_df) → TransformResult`
- `_drop_nulls_on_required(df, required_fields)` — drop rows missing required fields
- `_deduplicate(df, key_field)` — drop exact duplicates on primary key
- `_clean_strings(df, columns)` — strip, title-case name fields
- `_validate_numerics(df, columns)` — flag negative quantities/prices as warnings
- `_track_quality(original_count, final_df)` — compute quality metrics dict

### Step 13 — `app/services/transformers/sales.py`

Inherits `BaseTransformer`. Additional steps:
- Required fields: `invoice_date`, `product_name`, `quantity`, `total_amount`
- Deduplicate on `invoice_id`
- Flag rows where `total_amount <= 0` as warnings
- Validate `invoice_date` is not in the future

### Step 14 — `app/services/transformers/inventory.py`

- Required: `product_name`, `stock_quantity`
- Deduplicate on `product_id`
- Flag negative `stock_quantity`

### Step 15 — `app/services/transformers/purchases.py`

- Required: `purchase_date`, `supplier_name`, `total_cost`
- Deduplicate on `purchase_id`
- Flag `total_cost <= 0`

**Milestone check:** Run a dirty sales DataFrame through `SalesTransformer` → get back clean data + accurate quality metrics showing how many rows were dropped and why.

---

## Phase 8 — Analytics Layer

**Goal:** Compute KPIs from the clean Spark DataFrame. Pure functions, no side effects.

### Step 16 — `app/analytics/sales.py`

All functions take a Spark DataFrame and return a plain dict:

| Function | Returns |
|---|---|
| `total_revenue(df)` | `{"total_revenue": 1240000.0}` |
| `invoice_count(df)` | `{"invoice_count": 842}` |
| `unique_customers(df)` | `{"customer_count": 134}` |
| `average_order_value(df)` | `{"avg_order_value": 1472.7}` |
| `top_products(df, n=10)` | list of `{product_name, revenue, units_sold}` |
| `revenue_by_month(df)` | list of `{month, revenue}` |

### Step 17 — `app/analytics/inventory.py`

| Function | Returns |
|---|---|
| `total_products(df)` | count |
| `total_stock(df)` | sum of stock_quantity |
| `low_stock_items(df, threshold=10)` | list of products below threshold |
| `out_of_stock(df)` | count of zero-stock items |
| `stock_by_warehouse(df)` | list of `{warehouse, total_stock}` |
| `stock_by_category(df)` | list of `{category, total_stock}` |

### Step 18 — `app/analytics/purchases.py`

| Function | Returns |
|---|---|
| `total_purchase_cost(df)` | sum of total_cost |
| `purchase_order_count(df)` | count |
| `unique_suppliers(df)` | count |
| `average_purchase_value(df)` | mean |
| `top_suppliers(df, n=10)` | list of `{supplier_name, total_spend}` |
| `cost_by_month(df)` | list of `{month, total_cost}` |

---

## Phase 9 — API Endpoints

**Goal:** One endpoint per module. Same pipeline every time.

### Step 19 — `app/routers/analyze.py`

**Pipeline (identical for all three):**
```
POST /analyze/{module}
  → validate file (FileValidator)
  → save to temp
  → read with Pandas (FileReader)
  → map columns (ColumnMapper)
  → convert to Spark (DataFrameConverter)
  → transform/clean (SalesTransformer etc.)
  → run analytics (sales.py etc.)
  → return JSON response
  → cleanup temp file (BackgroundTasks)
```

**Response shape (same for all modules):**
```json
{
  "module": "sales",
  "filename": "sales_export.csv",
  "data_quality": {
    "uploaded_rows": 1200,
    "processed_rows": 1183,
    "dropped_rows": 17,
    "duplicate_rows": 5
  },
  "column_mapping": {
    "mapping": { "Invoice No": "invoice_id" },
    "coverage": 0.91,
    "unmapped_source": ["Internal Code"]
  },
  "kpis": {
    "total_revenue": 1240000.0,
    "invoice_count": 842,
    ...
  }
}
```

**Build order:**
1. `POST /analyze/sales` first — full pipeline
2. Verify it works end to end with a real file
3. Copy pattern for `POST /analyze/inventory`
4. Copy pattern for `POST /analyze/purchases`

---

## Phase 10 — Tests

**Goal:** Every layer tested before moving to the next one.

### Step 20 — `tests/conftest.py`

Fixtures:
- `spark` — session-scoped SparkSession (reused across all tests)
- `sample_sales_csv` — in-memory CSV string with known data
- `sample_sales_df` — Pandas DataFrame from above
- `tmp_csv_file` — writes sample CSV to a real temp file
- `client` — FastAPI `TestClient`

### Test files

| File | What it tests |
|---|---|
| `test_file_reader.py` | clean CSV, bad encoding, corrupt file, empty file |
| `test_column_mapper.py` | good mapping, low coverage, alias matching |
| `test_transformers.py` | dirty data in → clean data out, quality metrics accurate |
| `test_endpoints.py` | full pipeline via HTTP, bad file → correct error code |

---

## Phase 11 — Docker

**Goal:** One command to run everything.

### Step 21 — `Dockerfile`

- Base: `python:3.11-slim`
- Install Java 17 (required for PySpark): `apt-get install -y openjdk-17-jre-headless`
- Set `JAVA_HOME`
- Copy `requirements.txt`, install dependencies
- Copy app code
- Expose port 8000
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Step 22 — `docker-compose.yml`

Services:
- `api` — the FastAPI app built from Dockerfile
- Volumes: mount `./data` into container so Parquet output persists

> Note: No PostgreSQL needed for MVP — this design returns analytics as JSON per request.
> Add a DB later when you need to store processed results or job history.

---

## Build Order Summary

| Step | File | Milestone |
|---|---|---|
| 1-2 | `requirements.txt`, `requirements-dev.txt` | Dependencies locked |
| 3 | `app/config.py` | Settings load from .env |
| 4 | `app/main.py` | `/health` returns 200 |
| 5 | `app/utils/exceptions.py` | Structured errors defined |
| 6 | `app/utils/validators.py` | Bad files rejected correctly |
| 7 | `app/services/file_reader.py` | CSV/XLSX reads into DataFrame |
| 8-9 | `app/services/column_mapper.py` | Columns auto-mapped with confidence |
| 10 | `app/services/spark_session.py` | Spark starts and stops cleanly |
| 11 | `app/services/df_converter.py` | Pandas → Spark with type safety |
| 12 | `app/services/transformers/base.py` | Base cleaning logic done |
| 13-15 | `transformers/sales|inventory|purchases.py` | All three transformers working |
| 16-18 | `app/analytics/sales|inventory|purchases.py` | KPIs returning correct numbers |
| 19 | `app/routers/analyze.py` | `/analyze/sales` works end to end |
| 20 | `tests/` | All layers tested |
| 21-22 | `Dockerfile`, `docker-compose.yml` | Runs in one command |

---

## First Milestone (End of Step 4)

Before writing any file logic or Spark code, you should be able to:

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
# → {"status": "ok", "spark": "initializing"}
```

That means config loads, app starts, and the lifespan handler fires.
Everything after that is building layer by layer on a stable foundation.