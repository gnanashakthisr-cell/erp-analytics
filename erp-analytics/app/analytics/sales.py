import pandas as pd

def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

def _money(value) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), 2)

def _sales_pdf(df: pd.DataFrame) -> pd.DataFrame:
    pdf = df.copy()
    pdf["invoice_date"] = pd.to_datetime(pdf["invoice_date"], errors="coerce")
    for col_name in ["quantity", "unit_price", "total_amount"]:
        pdf[col_name] = pd.to_numeric(pdf[col_name], errors="coerce").fillna(0.0)
    return pdf

def compute_all(df: pd.DataFrame) -> dict:
    pdf = _sales_pdf(df)
    
    invoice_count_val = int(pdf["invoice_id"].count()) if "invoice_id" in pdf.columns else 0
    unique_invoices = int(pdf["invoice_id"].nunique(dropna=True)) if "invoice_id" in pdf.columns else 0
    avg_items = round(len(pdf) / unique_invoices, 2) if unique_invoices > 0 else 0
    
    customer_count = int(pdf["customer_id"].nunique(dropna=True)) if "customer_id" in pdf.columns else 0
    if customer_count == 0 and "customer_name" in pdf.columns:
        customer_count = int(pdf["customer_name"].nunique(dropna=True))
        
    product_count = int(pdf["product_id"].nunique(dropna=True)) if "product_id" in pdf.columns else 0
    if product_count == 0 and "product_name" in pdf.columns:
        product_count = int(pdf["product_name"].nunique(dropna=True))

    dated = pdf.dropna(subset=["invoice_date"]).copy() if "invoice_date" in pdf.columns else pd.DataFrame()
    revenue_by_month_rows = []
    revenue_by_quarter_rows = []
    sales_by_day_rows = []
    
    if not dated.empty:
        dated["year"] = dated["invoice_date"].dt.year
        dated["month"] = dated["invoice_date"].dt.month
        dated["quarter"] = dated["invoice_date"].dt.quarter
        dated["day_of_week"] = ((dated["invoice_date"].dt.dayofweek + 1) % 7) + 1
        
        revenue_by_month_rows = [
            {"year": int(r["year"]), "month": int(r["month"]), "revenue": _money(r["total_amount"])}
            for _, r in dated.groupby(["year", "month"], as_index=False)["total_amount"].sum().iterrows()
        ]
        revenue_by_quarter_rows = [
            {"year": int(r["year"]), "quarter": int(r["quarter"]), "revenue": _money(r["total_amount"])}
            for _, r in dated.groupby(["year", "quarter"], as_index=False)["total_amount"].sum().iterrows()
        ]
        day_group = dated.groupby("day_of_week", as_index=False, dropna=False).agg(
            revenue=("total_amount", "sum"),
            order_count=("invoice_id" if "invoice_id" in dated.columns else "total_amount", "count"),
        )
        sales_by_day_rows = [
            {"day_of_week": int(r["day_of_week"]), "revenue": _money(r["revenue"]),
             "order_count": int(r["order_count"])}
            for _, r in day_group.iterrows()
        ]

    branch_group = (
        pdf.groupby("branch", as_index=False, dropna=False)["total_amount"]
        .sum()
        .sort_values("total_amount", ascending=False)
    ) if "branch" in pdf.columns else pd.DataFrame()
    
    product_revenue = (
        pdf.groupby("product_name", as_index=False, dropna=False)
        .agg(revenue=("total_amount", "sum"), units_sold=("quantity", "sum"))
        .sort_values("revenue", ascending=False)
        .head(20)
    ) if "product_name" in pdf.columns else pd.DataFrame()
    
    product_qty = product_revenue.sort_values("units_sold", ascending=False).head(20) if not product_revenue.empty else pd.DataFrame()
    
    cust_group_cols = [c for c in ["customer_id", "customer_name"] if c in pdf.columns]
    customer_revenue = (
        pdf.groupby(cust_group_cols, as_index=False, dropna=False)
        .agg(revenue=("total_amount", "sum"), order_count=("invoice_id" if "invoice_id" in pdf.columns else "total_amount", "count"))
    ) if cust_group_cols else pd.DataFrame()
    
    top_customer_revenue = customer_revenue.sort_values("revenue", ascending=False).head(20) if not customer_revenue.empty else pd.DataFrame()
    top_customer_frequency = customer_revenue.sort_values("order_count", ascending=False).head(20) if not customer_revenue.empty else pd.DataFrame()

    customer_key = "customer_id" if ("customer_id" in pdf.columns and int(pdf["customer_id"].nunique(dropna=True)) > 0) else "customer_name"
    customer_totals = pdf.groupby(customer_key, dropna=False)["total_amount"].sum() if customer_key in pdf.columns else pd.Series(dtype=float)
    revenues = [float(v or 0) for v in customer_totals.tolist()]
    
    if revenues:
        max_rev = max(revenues)
        high = sum(1 for r in revenues if r >= max_rev * 0.5)
        medium = sum(1 for r in revenues if max_rev * 0.2 <= r < max_rev * 0.5)
        low = sum(1 for r in revenues if r < max_rev * 0.2)
    else:
        high = medium = low = 0

    mean_amount = float(pdf["total_amount"].mean() or 0)
    threshold = mean_amount * 3.0
    anomaly_rows = (
        pdf[pdf["total_amount"] > threshold]
        .sort_values("total_amount", ascending=False)
        .head(20)
    )

    return {
        "overview": {
            "total_revenue": _money(pdf["total_amount"].sum()),
            "invoice_count": invoice_count_val,
            "customer_count": customer_count,
            "product_count": product_count,
            "avg_order_value": _money(pdf["total_amount"].mean()),
            "avg_items_per_order": avg_items,
        },
        "revenue_by_month": revenue_by_month_rows,
        "revenue_by_quarter": revenue_by_quarter_rows,
        "revenue_by_branch": [
            {"branch": _json_value(r.get("branch")), "revenue": _money(r.get("total_amount"))}
            for _, r in branch_group.iterrows()
        ],
        "top_products_by_revenue": [
            {"product_name": _json_value(r.get("product_name")), "revenue": _money(r.get("revenue")),
             "units_sold": _money(r.get("units_sold"))}
            for _, r in product_revenue.iterrows()
        ],
        "top_products_by_quantity": [
            {"product_name": _json_value(r.get("product_name")), "units_sold": _money(r.get("units_sold")),
             "revenue": _money(r.get("revenue"))}
            for _, r in product_qty.iterrows()
        ],
        "top_customers_by_revenue": [
            {"customer_id": _json_value(r.get("customer_id")), "customer_name": _json_value(r.get("customer_name")),
             "revenue": _money(r.get("revenue"))}
            for _, r in top_customer_revenue.iterrows()
        ],
        "top_customers_by_frequency": [
            {"customer_id": _json_value(r.get("customer_id")), "customer_name": _json_value(r.get("customer_name")),
             "order_count": int(r.get("order_count", 0)), "revenue": _money(r.get("revenue"))}
            for _, r in top_customer_frequency.iterrows()
        ],
        "customer_segmentation": {"high_value": high, "medium_value": medium, "low_value": low},
        "sales_by_day_of_week": sales_by_day_rows,
        "anomalies": {
            "high_value_orders": [
                {"invoice_id": _json_value(r.get("invoice_id")), "total_amount": _money(r.get("total_amount")),
                 "customer_name": _json_value(r.get("customer_name")),
                 "invoice_date": None if pd.isna(r.get("invoice_date")) else str(r.get("invoice_date").date())}
                for _, r in anomaly_rows.iterrows()
            ],
        },
    }
