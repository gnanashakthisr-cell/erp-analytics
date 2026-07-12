import pandas as pd

from app.services.transformers.base import BaseTransformer, TransformResult


REQUIRED_FIELDS = ["product_name", "stock_quantity"]
STRING_FIELDS = ["product_id", "product_name", "category", "unit", "warehouse"]
NUMERIC_FIELDS = ["stock_quantity"]


class InventoryTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> TransformResult:
        original_count = len(df)

        df = df.dropna(subset=REQUIRED_FIELDS).copy()

        before_dedup = len(df)
        if "product_id" in df.columns:
            df = df.drop_duplicates(subset=["product_id"])
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

        if "stock_quantity" in df.columns:
            neg_stock = int((df["stock_quantity"] < 0).sum())
            if neg_stock > 0:
                num_warnings.append(f"{neg_stock} products have negative stock_quantity")

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
