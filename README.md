# ERP Analytics Platform — Instant Insights 📊

An open-source, stateless ETL and analytics engine designed to instantly analyze exports from any ERP system. Users simply upload a CSV or XLSX file, the engine automatically maps column headers, runs data-quality and cleaning operations using PySpark, and outputs rich interactive insights on a dashboard.

---

## 🚀 Getting Started

### 1. Run the Backend (FastAPI)
The backend requires **Python 3.11** and **Java 17** (for PySpark).

```bash
cd erp-analytics
# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Verify the backend is running by opening: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Run the Frontend (Vite)
The frontend is a vanilla Vite project with Chart.js.

```bash
cd frontend
# Install dependencies
npm install

# Start development server
npm run dev
```
Open your browser to: [http://localhost:3000](http://localhost:3000)

---

## 📁 Sample Datasets for Testing

To make testing easy, a suite of sample ERP exports has been generated in the project. These datasets include varied column naming conventions, date formats, currencies, and dirty/duplicate rows to showcase the engine's auto-mapping and cleanup capabilities.

### 💰 Sales Module
* **[sales_format1.csv](file:///d:/opensource%20ETL/samples/sales/sales_format1.csv)**: Standard schema with clean headers (`Invoice ID`, `Customer Name`, etc.).
* **[sales_format2.xlsx](file:///d:/opensource%20ETL/samples/sales/sales_format2.xlsx)**: Excel spreadsheet using shorthand ERP column names (`Inv No.`, `Qty Sold`, `Rate`, `Curr`).
* **[sales_format3.csv](file:///d:/opensource%20ETL/samples/sales/sales_format3.csv)**: Dirty CSV featuring missing invoice IDs, zero-quantity records, and diverse date formats (`dd-mmm-yy`) to test data cleanup and dropping filters.

### 📦 Inventory Module
* **[inventory_format1.csv](file:///d:/opensource%20ETL/samples/inventory/inventory_format1.csv)**: Standard inventory snapshot (`Product ID`, `Stock Quantity`, `Warehouse`).
* **[inventory_format2.xlsx](file:///d:/opensource%20ETL/samples/inventory/inventory_format2.xlsx)**: Excel file with alternative headers (`Item Code`, `QOH`, `Snapshot Date`).
* **[inventory_format3.csv](file:///d:/opensource%20ETL/samples/inventory/inventory_format3.csv)**: CSV format using SKU identifiers and store codes.

### 🛒 Purchases Module
* **[purchases_format1.csv](file:///d:/opensource%20ETL/samples/purchases/purchases_format1.csv)**: Clean procurement ledger containing supplier and cost records.
* **[purchases_format2.xlsx](file:///d:/opensource%20ETL/samples/purchases/purchases_format2.xlsx)**: Purchase orders in Excel using vendor codes (`PO Number`, `Vendor`, `Total Amount`).
* **[purchases_format3.csv](file:///d:/opensource%20ETL/samples/purchases/purchases_format3.csv)**: CSV referencing POs as transaction records (`Reference No`, `Buying Price`).

---

## ⚙️ How it Works under the Hood

1. **Auto Column Mapping**: Uses fuzzy string matching via [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) to automatically align varied ERP column headers (e.g., matching `"Qty Sold"`, `"Volume"`, `"PCS"`, and `"units"` to the standard field `quantity`).
2. **Type Coercion & Bridging**: Converts the Pandas DataFrame into a typed PySpark DataFrame. Dates, amounts, and numbers are coerced into standard database types.
3. **Data Quality Filter**: Drops duplicate entries, validates numerical fields (warns on negative values), handles null fields, and computes completeness metrics.
4. **KPI & Analytics Aggregator**: Dynamically calculates business performance metrics (growth rates, customer segments, top categories, anomaly outliers) and returns them in a standard JSON response.
5. **Interactive Dashboard**: Dynamically draws responsive lines, doughnut, and bar charts using **Chart.js** alongside glassmorphic KPI status cards.
