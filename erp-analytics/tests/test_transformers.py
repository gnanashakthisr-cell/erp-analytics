import pandas as pd
from app.services.transformers.sales import SalesTransformer
from app.services.transformers.inventory import InventoryTransformer
from app.services.transformers.purchases import PurchasesTransformer


def test_sales_transformer_basic():
    data = {
        "invoice_id": ["INV-001", "INV-002"],
        "invoice_date": ["2024-01-15", "2024-02-20"],
        "customer_id": ["C1", "C2"],
        "customer_name": ["Cust A", "Cust B"],
        "product_id": ["P1", "P2"],
        "product_name": ["Widget", "Gadget"],
        "quantity": [10.0, 5.0],
        "unit_price": [100.0, 200.0],
        "total_amount": [1000.0, 1000.0],
        "branch": ["Main", "Main"],
        "currency": ["USD", "USD"]
    }
    df = pd.DataFrame(data)
    result = SalesTransformer().transform(df)
    assert result.processed_rows == 2
    assert result.duplicate_rows == 0


def test_sales_transformer_deduplicates():
    data = {
        "invoice_id": ["INV-001", "INV-001"],
        "invoice_date": ["2024-01-15", "2024-01-15"],
        "customer_id": ["C1", "C1"],
        "customer_name": ["Cust A", "Cust A"],
        "product_id": ["P1", "P1"],
        "product_name": ["Widget", "Widget"],
        "quantity": [10.0, 10.0],
        "unit_price": [100.0, 100.0],
        "total_amount": [1000.0, 1000.0],
        "branch": ["Main", "Main"],
        "currency": ["USD", "USD"]
    }
    df = pd.DataFrame(data)
    result = SalesTransformer().transform(df)
    assert result.processed_rows == 1
    assert result.duplicate_rows == 1


def test_inventory_transformer():
    data = {
        "product_id": ["P1", "P2"],
        "product_name": ["Widget", "Gadget"],
        "category": ["Electronics", "Electronics"],
        "stock_quantity": [50.0, -5.0],
        "unit": ["pcs", "pcs"],
        "warehouse": ["WH-A", "WH-B"],
        "last_updated": ["2024-01-15", "2024-01-20"]
    }
    df = pd.DataFrame(data)
    result = InventoryTransformer().transform(df)
    assert result.processed_rows == 2
    assert "negative" in result.quality_metrics.get("warnings", [])[0]


def test_purchases_transformer():
    data = {
        "purchase_id": ["PO-001"],
        "purchase_date": ["2024-01-15"],
        "supplier_id": ["S1"],
        "supplier_name": ["Supplier A"],
        "product_id": ["P1"],
        "product_name": ["Widget"],
        "quantity": [10.0],
        "unit_cost": [100.0],
        "total_cost": [1000.0],
        "currency": ["USD"]
    }
    df = pd.DataFrame(data)
    result = PurchasesTransformer().transform(df)
    assert result.processed_rows == 1
