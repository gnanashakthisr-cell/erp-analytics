import pytest
from app.services.column_mapper import ColumnMapper
from app.utils.exceptions import MappingCoverageError


def test_good_sales_mapping():
    columns = ["Invoice No", "Date", "Customer Name", "Product Name",
               "Qty", "Rate", "Amount", "Branch"]
    mapper = ColumnMapper()
    result = mapper.map_columns(columns, "sales")
    assert result.coverage >= 0.80
    assert "invoice_id" in result.confidence
    assert "invoice_date" in result.confidence


def test_partial_mapping_raises_error():
    columns = ["Col A", "Col B", "Col C"]
    mapper = ColumnMapper()
    with pytest.raises(MappingCoverageError):
        mapper.map_columns(columns, "sales")


def test_alias_matching():
    columns = ["Inv No", "Inv Date", "Cust Name", "Item", "Qty Sold", "Unit Price", "Total"]
    mapper = ColumnMapper()
    result = mapper.map_columns(columns, "sales")
    assert "invoice_id" in result.mapping.values()
    assert "invoice_date" in result.mapping.values()


def test_unmapped_source_columns():
    columns = ["Invoice No", "Date", "Customer", "Product", "Qty", "Rate", "Amount", "Extra Field"]
    mapper = ColumnMapper()
    result = mapper.map_columns(columns, "sales")
    assert "Extra Field" in result.unmapped_source
