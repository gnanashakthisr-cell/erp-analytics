from dataclasses import dataclass, field

import pandas as pd

from app.utils.exceptions import CorruptFileError


@dataclass
class FileReadResult:
    df: pd.DataFrame
    filename: str
    columns: list[str]
    row_count: int
    preview: list[dict]
    null_stats: dict[str, float]
    warnings: list[str] = field(default_factory=list)


class FileReader:
    @staticmethod
    def read(file_path: str, filename: str) -> FileReadResult:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            FileReader._reject_null_bytes(file_path)
        try:
            if ext == "csv":
                df = FileReader._read_csv(file_path)
            else:
                df = FileReader._read_excel(file_path)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError, OSError) as e:
            raise CorruptFileError(str(e))

        df.columns = [str(c).strip() for c in df.columns]

        null_stats = {col: round(df[col].isnull().mean(), 4) for col in df.columns}
        warnings = []
        for col, null_pct in null_stats.items():
            if null_pct > 0.5:
                warnings.append(f"Column '{col}' is {null_pct:.0%} null")

        return FileReadResult(
            df=df,
            filename=filename,
            columns=list(df.columns),
            row_count=len(df),
            preview=df.head(10).to_dict(orient="records"),
            null_stats=null_stats,
            warnings=warnings,
        )

    @staticmethod
    def _read_csv(file_path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(file_path, engine="pyarrow")
        except Exception:
            pass
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                return pd.read_csv(file_path, encoding=enc, sep=None, engine="python")
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise CorruptFileError("Could not decode CSV with utf-8, latin-1, or cp1252")

    @staticmethod
    def _read_excel(file_path: str) -> pd.DataFrame:
        return pd.read_excel(file_path, engine="openpyxl")

    @staticmethod
    def _reject_null_bytes(file_path: str) -> None:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                if b"\x00" in chunk:
                    raise CorruptFileError("File contains null bytes")
