import pandas as pd

def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

def _num(value) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), 2)

def _inventory_pdf(df: pd.DataFrame) -> pd.DataFrame:
    pdf = df.copy()
    pdf["stock_quantity"] = pd.to_numeric(pdf["stock_quantity"], errors="coerce").fillna(0.0)
    return pdf

def compute_all(df: pd.DataFrame) -> dict:
    pdf = _inventory_pdf(df)
    total_products = int(pdf["product_id"].nunique(dropna=True)) if "product_id" in pdf.columns else 0
    if total_products == 0 and "product_name" in pdf.columns:
        total_products = int(pdf["product_name"].nunique(dropna=True))
        
    stock_by_category_rows = (
        pdf.groupby("category", as_index=False, dropna=False)["stock_quantity"]
        .sum()
        .sort_values("stock_quantity", ascending=False)
    ) if "category" in pdf.columns else pd.DataFrame()
    
    stock_by_warehouse_rows = (
        pdf.groupby("warehouse", as_index=False, dropna=False)["stock_quantity"]
        .sum()
        .sort_values("stock_quantity", ascending=False)
    ) if "warehouse" in pdf.columns else pd.DataFrame()

    total_stock = float(pdf["stock_quantity"].sum() or 1)
    
    group_cols = [c for c in ["product_id", "product_name"] if c in pdf.columns]
    abc_rows = (
        pdf.groupby(group_cols, as_index=False, dropna=False)["stock_quantity"]
        .sum()
        .sort_values("stock_quantity", ascending=False)
    ) if group_cols else pd.DataFrame()
    
    cumulative = 0.0
    a_items = []
    b_items = []
    c_items = []
    for _, r in abc_rows.iterrows():
        pct = float(r["stock_quantity"] or 0) / total_stock
        cumulative += pct
        item = {
            "product_id": _json_value(r.get("product_id")),
            "product_name": _json_value(r.get("product_name")),
            "stock": _num(r["stock_quantity"]),
            "percentage": round(pct, 4),
        }
        if cumulative <= 0.8:
            a_items.append(item)
        elif cumulative <= 0.95:
            b_items.append(item)
        else:
            c_items.append(item)

    low_stock = (
        pdf[(pdf["stock_quantity"] > 0) & (pdf["stock_quantity"] < 10.0)]
        .sort_values("stock_quantity")
        .head(50)
    )
    mean_stock = float(pdf["stock_quantity"].mean() or 0)
    overstock = (
        pdf[pdf["stock_quantity"] > mean_stock * 3]
        .sort_values("stock_quantity", ascending=False)
        .head(20)
    )

    stock_by_category = [
        {"category": _json_value(r.get("category")), "total_stock": _num(r["stock_quantity"])}
        for _, r in stock_by_category_rows.iterrows()
    ]
    stock_by_warehouse = [
        {"warehouse": _json_value(r.get("warehouse")), "total_stock": _num(r["stock_quantity"])}
        for _, r in stock_by_warehouse_rows.iterrows()
    ]

    return {
        "overview": {
            "total_products": total_products,
            "total_stock_units": _num(pdf["stock_quantity"].sum()),
            "total_warehouses": int(pdf["warehouse"].nunique(dropna=True)) if "warehouse" in pdf.columns else 0,
            "total_categories": int(pdf["category"].nunique(dropna=True)) if "category" in pdf.columns else 0,
            "out_of_stock_count": int((pdf["stock_quantity"] == 0).sum()),
            "low_stock_count": int(((pdf["stock_quantity"] > 0) & (pdf["stock_quantity"] < 10.0)).sum()),
        },
        "stock_by_category": stock_by_category,
        "stock_by_warehouse": stock_by_warehouse,
        "valuation": {
            "total_inventory_value": _num(pdf["stock_quantity"].sum()),
            "value_by_category": [
                {"category": item["category"], "value": item["total_stock"]}
                for item in stock_by_category
            ],
            "value_by_warehouse": [
                {"warehouse": item["warehouse"], "value": item["total_stock"]}
                for item in stock_by_warehouse
            ],
        },
        "abc_analysis": {"a_items": a_items, "b_items": b_items, "c_items": c_items},
        "recommendations": {
            "reorder": [
                {"product_id": _json_value(r.get("product_id")), "product_name": _json_value(r.get("product_name")),
                 "current_stock": _num(r["stock_quantity"])}
                for _, r in low_stock.iterrows()
            ],
            "overstock": [
                {"product_id": _json_value(r.get("product_id")), "product_name": _json_value(r.get("product_name")),
                 "stock_quantity": _num(r["stock_quantity"])}
                for _, r in overstock.iterrows()
            ],
        },
    }
