import pytest
import pandas as pd
from app.services.file_reader import FileReader
from app.utils.exceptions import CorruptFileError


def test_read_csv(sample_sales_csv):
    result = FileReader.read(sample_sales_csv, "test_sales.csv")
    assert result.row_count == 3
    assert len(result.columns) == 7
    assert result.preview is not None
    assert isinstance(result.null_stats, dict)


def test_read_csv_with_extra_spaces_in_columns(tmp_csv_file):
    df = pd.DataFrame({"  Invoice No  ": [1], "  Date  ": ["2024-01-01"]})
    path = tmp_csv_file(df, "spaced.csv")
    result = FileReader.read(path, "spaced.csv")
    assert all(c == c.strip() for c in result.columns)


def test_read_empty_csv(tmp_csv_file):
    df = pd.DataFrame()
    path = tmp_csv_file(df, "empty.csv")
    result = FileReader.read(path, "empty.csv")
    assert result.row_count == 0


def test_read_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.csv"
    path.write_text("not,a,csv,content\n\x00\x00\x00garbage")
    with pytest.raises(CorruptFileError):
        FileReader.read(str(path), "corrupt.csv")
