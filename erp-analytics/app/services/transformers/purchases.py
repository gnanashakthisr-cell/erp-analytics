import pandas as pd

from app.services.transformers.base import BaseTransformer, TransformResult


REQUIRED_FIELDS = ["purchase_date", "supplier_name", "total_cost"]
STRING_FIELDS = ["purchase_id", "supplier_id", "supplier_name", "product_id",
                 "product_name", "currency"]
NUMERIC_FIELDS = ["quantity", "unit_cost", "total_cost"]


class PurchasesTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> TransformResult:
        original_count = len(df)

        df = df.dropna(subset=REQUIRED_FIELDS).copy()

        before_dedup = len(df)
        if "purchase_id" in df.columns:
            df = df.drop_duplicates(subset=["purchase_id"])
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

        if "total_cost" in df.columns:
            neg_cost = int((df["total_cost"] <= 0).sum())
            if neg_cost > 0:
                num_warnings.append(f"{neg_cost} rows with total_cost <= 0")

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
