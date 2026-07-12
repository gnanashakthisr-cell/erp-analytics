from datetime import date

import pandas as pd

from app.services.transformers.base import BaseTransformer, TransformResult


REQUIRED_FIELDS = ["invoice_date", "product_name", "quantity", "total_amount"]
STRING_FIELDS = ["invoice_id", "customer_id", "customer_name", "product_id",
                 "product_name", "branch", "currency"]
NUMERIC_FIELDS = ["quantity", "unit_price", "total_amount"]


class SalesTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> TransformResult:
        original_count = len(df)

        df = df.dropna(subset=REQUIRED_FIELDS).copy()

        before_dedup = len(df)
        if "invoice_id" in df.columns:
            df = df.drop_duplicates(subset=["invoice_id"])
        else:
            df = df.drop_duplicates()
        duplicate_count = before_dedup - len(df)

        for c in STRING_FIELDS:
            if c in df.columns:
                df[c] = df[c].apply(lambda val: None if pd.isna(val) else str(val).strip())

        num_warnings = []
        for c in NUMERIC_FIELDS:
            if c in df.columns:
                neg_count = int((df[c] < 0).sum())
                if neg_count > 0:
                    num_warnings.append(f"Column '{c}' has {neg_count} negative values")

        today = date.today()
        if "invoice_date" in df.columns:
            invoice_dates = pd.to_datetime(df["invoice_date"], errors="coerce").dt.date
            future_count = int((invoice_dates > today).sum())
            if future_count > 0:
                num_warnings.append(f"{future_count} rows have future invoice_date")

        if "total_amount" in df.columns:
            zero_amt = int((df["total_amount"] <= 0).sum())
            if zero_amt > 0:
                num_warnings.append(f"{zero_amt} rows with total_amount <= 0")

        processed_rows = len(df)
        dropped_rows = original_count - processed_rows - duplicate_count
        quality = {
            "uploaded_rows": original_count,
            "processed_rows": processed_rows,
            "dropped_rows": dropped_rows,
            "duplicate_rows": duplicate_count,
            "warnings": num_warnings,
        }

        return TransformResult(
            df=df,
            uploaded_rows=original_count,
            processed_rows=processed_rows,
            dropped_rows=dropped_rows,
            duplicate_rows=duplicate_count,
            quality_metrics=quality,
        )
