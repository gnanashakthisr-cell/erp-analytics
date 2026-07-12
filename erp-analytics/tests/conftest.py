import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame({
        "Invoice No": ["INV-001", "INV-002", "INV-003"],
        "Date": ["2024-01-15", "2024-02-20", "2024-03-10"],
        "Customer": ["Cust A", "Cust B", "Cust A"],
        "Product": ["Widget X", "Widget Y", "Widget X"],
        "Qty": [10, 5, 3],
        "Rate": [100.0, 200.0, 100.0],
        "Amount": [1000.0, 1000.0, 300.0],
    })


@pytest.fixture
def sample_sales_csv(tmp_path, sample_sales_df):
    path = tmp_path / "test_sales.csv"
    sample_sales_df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def tmp_csv_file(tmp_path):
    def _make(df: pd.DataFrame, name: str = "test.csv") -> str:
        path = tmp_path / name
        df.to_csv(path, index=False)
        return str(path)
    return _make
