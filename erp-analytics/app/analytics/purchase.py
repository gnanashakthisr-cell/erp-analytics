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

def _purchase_pdf(df: pd.DataFrame) -> pd.DataFrame:
    pdf = df.copy()
    pdf["purchase_date"] = pd.to_datetime(pdf["purchase_date"], errors="coerce")
    for col_name in ["quantity", "unit_cost", "total_cost"]:
        pdf[col_name] = pd.to_numeric(pdf[col_name], errors="coerce").fillna(0.0)
    return pdf

def compute_all(df: pd.DataFrame) -> dict:
    pdf = _purchase_pdf(df)
    
    purchase_count = int(pdf["purchase_id"].count()) if "purchase_id" in pdf.columns else 0
    unique_purchases = int(pdf["purchase_id"].nunique(dropna=True)) if "purchase_id" in pdf.columns else 0
    avg_items = round(len(pdf) / unique_purchases, 2) if unique_purchases > 0 else 0
    
    supplier_count = int(pdf["supplier_id"].nunique(dropna=True)) if "supplier_id" in pdf.columns else 0
    if supplier_count == 0 and "supplier_name" in pdf.columns:
        supplier_count = int(pdf["supplier_name"].nunique(dropna=True))
        
    product_count = int(pdf["product_id"].nunique(dropna=True)) if "product_id" in pdf.columns else 0
    if product_count == 0 and "product_name" in pdf.columns:
        product_count = int(pdf["product_name"].nunique(dropna=True))

    dated = pdf.dropna(subset=["purchase_date"]).copy() if "purchase_date" in pdf.columns else pd.DataFrame()
    cost_by_month_rows = []
    
    if not dated.empty:
        dated["year"] = dated["purchase_date"].dt.year
        dated["month"] = dated["purchase_date"].dt.month
        cost_by_month_rows = [
            {"year": int(r["year"]), "month": int(r["month"]), "total_cost": _num(r["total_cost"])}
            for _, r in dated.groupby(["year", "month"], as_index=False)["total_cost"].sum().iterrows()
        ]

    sup_group_cols = [c for c in ["supplier_id", "supplier_name"] if c in pdf.columns]
    supplier_group = (
        pdf.groupby(sup_group_cols, as_index=False, dropna=False)
        .agg(total_spend=("total_cost", "sum"), order_count=("purchase_id" if "purchase_id" in pdf.columns else "total_cost", "count"))
    ) if sup_group_cols else pd.DataFrame()
    
    top_suppliers_spend = supplier_group.sort_values("total_spend", ascending=False).head(20) if not supplier_group.empty else pd.DataFrame()
    top_suppliers_frequency = supplier_group.sort_values("order_count", ascending=False).head(20) if not supplier_group.empty else pd.DataFrame()
    
    total_spend = float(pdf["total_cost"].sum() or 1)
    top5 = supplier_group.sort_values("total_spend", ascending=False).head(5) if not supplier_group.empty else pd.DataFrame()
    top5_concentration = float(top5["total_spend"].sum() or 0) / total_spend if not top5.empty else 0.0

    prod_group_cols = [c for c in ["product_id", "product_name"] if c in pdf.columns]
    product_group = (
        pdf.groupby(prod_group_cols, as_index=False, dropna=False)
        .agg(total_cost=("total_cost", "sum"), total_quantity=("quantity", "sum"))
        .sort_values("total_cost", ascending=False)
        .head(20)
    ) if prod_group_cols else pd.DataFrame()

    return {
        "overview": {
            "total_purchase_cost": _num(pdf["total_cost"].sum()),
            "purchase_order_count": purchase_count,
            "supplier_count": supplier_count,
            "products_purchased_count": product_count,
            "avg_purchase_value": _num(pdf["total_cost"].mean()),
            "avg_items_per_purchase": avg_items,
        },
        "cost_by_month": cost_by_month_rows,
        "supplier_intelligence": {
            "top_suppliers_by_spend": [
                {"supplier_id": _json_value(r.get("supplier_id")), "supplier_name": _json_value(r.get("supplier_name")),
                 "total_spend": _num(r.get("total_spend"))}
                for _, r in top_suppliers_spend.iterrows()
            ],
            "top_suppliers_by_frequency": [
                {"supplier_id": _json_value(r.get("supplier_id")), "supplier_name": _json_value(r.get("supplier_name")),
                 "order_count": int(r.get("order_count", 0)), "total_spend": _num(r.get("total_spend"))}
                for _, r in top_suppliers_frequency.iterrows()
            ],
            "top_5_suppliers": [
                {"supplier_id": _json_value(r.get("supplier_id")), "supplier_name": _json_value(r.get("supplier_name")),
                 "spend": _num(r.get("total_spend")), "percentage": round(float(r.get("total_spend") or 0) / total_spend, 4)}
                for _, r in top5.iterrows()
            ],
            "top_5_concentration": round(top5_concentration, 4),
        },
        "top_products_by_cost": [
            {"product_id": _json_value(r.get("product_id")), "product_name": _json_value(r.get("product_name")),
             "total_cost": _num(r.get("total_cost")), "total_quantity": _num(r.get("total_quantity"))}
            for _, r in product_group.iterrows()
        ],
    }
