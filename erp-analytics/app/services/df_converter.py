from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d-%b-%Y",
    "%d-%b-%y",
]

@dataclass
class ConversionResult:
    pandas_df: pd.DataFrame
    total_rows: int
    converted_rows: int
    rejected_rows: int
    rejection_reasons: list[str] = field(default_factory=list)

MODULE_TYPE_MAP = {
    "sales": {
        "string": ["invoice_id", "customer_id", "customer_name", "product_id",
                    "product_name", "branch", "currency"],
        "double": ["quantity", "unit_price", "total_amount"],
        "date": ["invoice_date"],
    },
    "inventory": {
        "string": ["product_id", "product_name", "category", "unit", "warehouse"],
        "double": ["stock_quantity"],
        "date": ["last_updated"],
    },
    "purchases": {
        "string": ["purchase_id", "supplier_id", "supplier_name", "product_id",
                    "product_name", "currency"],
        "double": ["quantity", "unit_cost", "total_cost"],
        "date": ["purchase_date"],
    },
}

class DataFrameConverter:
    def convert(self, pandas_df: pd.DataFrame, mapping: dict[str, str], module: str) -> ConversionResult:
        typed_df = MODULE_TYPE_MAP.get(module)
        if typed_df is None:
            raise ValueError(f"Unknown module: {module}")

        renamed = pandas_df.rename(columns=mapping)

        rejection_reasons = []
        total_rows = len(renamed)

        for col in renamed.columns:
            if col in typed_df["double"]:
                renamed[col] = pd.to_numeric(renamed[col], errors="coerce").astype("Float64")
                bad = renamed[col].isna().sum()
                if bad > 0:
                    rejection_reasons.append(f"{bad} rows with non-numeric values in '{col}'")

            elif col in typed_df["date"]:
                def parse_date(val):
                    if pd.isna(val):
                        return None
                    if isinstance(val, datetime):
                        return val.date()
                    for fmt in DATE_FORMATS:
                        try:
                            return datetime.strptime(str(val).strip(), fmt).date()
                        except (ValueError, TypeError):
                            continue
                    return None

                parsed = renamed[col].apply(parse_date)
                bad = parsed.isna().sum()
                if bad > 0:
                    rejection_reasons.append(f"{bad} rows with unparseable dates in '{col}'")
                renamed[col] = parsed

            elif col in typed_df["string"]:
                renamed[col] = renamed[col].apply(
                    lambda val: pd.NA if pd.isna(val) else str(val).strip()
                ).astype("string")

        for col in typed_df["string"]:
            if col not in renamed.columns:
                renamed[col] = pd.Series(pd.NA, index=renamed.index, dtype="string")

        for col in typed_df["double"]:
            if col not in renamed.columns:
                renamed[col] = pd.Series(0.0, index=renamed.index, dtype="Float64")

        for col in typed_df["date"]:
            if col not in renamed.columns:
                renamed[col] = pd.Series(None, index=renamed.index)

        renamed = renamed.fillna({c: 0.0 for c in typed_df["double"]})
        canonical_columns = typed_df["string"] + typed_df["double"] + typed_df["date"]
        renamed = renamed[canonical_columns]

        processed_rows = len(renamed)
        rejected_rows = total_rows - processed_rows

        return ConversionResult(
            pandas_df=renamed,
            total_rows=total_rows,
            converted_rows=processed_rows,
            rejected_rows=rejected_rows,
            rejection_reasons=rejection_reasons,
        )
