import io

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_analyze_sales_with_csv(tmp_path):
    csv_content = ("Invoice No,Date,Customer,Product,Qty,Rate,Amount\n"
                   "INV-001,2024-01-15,Cust A,Widget X,10,100,1000\n"
                   "INV-002,2024-02-20,Cust B,Widget Y,5,200,1000\n")

    resp = client.post(
        "/analyze/sales",
        files={"file": ("test_sales.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "sales"
    assert "data_quality" in data
    assert "kpis" in data
    assert "overview" in data["kpis"]


def test_analyze_invalid_module():
    csv_content = "a,b,c\n1,2,3\n"
    resp = client.post(
        "/analyze/invalid",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 404


def test_analyze_bad_extension():
    resp = client.post(
        "/analyze/sales",
        files={"file": ("test.exe", io.BytesIO(b"fake"), "application/x-msdownload")},
    )
    assert resp.status_code == 415


def test_analyze_empty_file():
    resp = client.post(
        "/analyze/sales",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert resp.status_code in (400, 422)
