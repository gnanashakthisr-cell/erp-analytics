from dataclasses import dataclass, field

from rapidfuzz import process

from app.utils.exceptions import MappingCoverageError


REQUIRED_COVERAGE = 0.80


SALES_ALIASES = {
    "invoice_id": ["invoice no", "invoice no.", "inv no", "inv no.", "inv id", "invoice id",
                   "bill no", "bill no.", "voucher no", "voucher number", "invoice number",
                   "doc no", "document no", "order id", "transaction id"],
    "invoice_date": ["invoice date", "inv date", "date", "transaction date", "doc date",
                     "document date", "order date", "bill date", "posting date", "created date",
                     "transaction date", "sales date"],
    "customer_id": ["customer id", "cust id", "customer code", "cust code", "client id",
                    "client code", "customer no", "customer number", "party id", "account id",
                    "customer id no", "cust id no"],
    "customer_name": ["customer name", "cust name", "customer", "client", "client name", "party name",
                      "account name", "customer desc", "customer description", "bill to"],
    "product_id": ["product id", "prod id", "item id", "item code", "product code", "sku",
                   "sku code", "material id", "material code", "part no", "part number", "article no"],
    "product_name": ["product name", "prod name", "item name", "item desc", "product desc",
                     "product description", "item description", "material desc", "description",
                     "article name", "product", "item", "material"],
    "quantity": ["quantity", "qty", "qty sold", "qty ordered", "units", "units sold",
                 "sales qty", "order qty", "piece", "pcs", "count", "volume"],
    "unit_price": ["unit price", "unit rate", "price", "rate", "selling price", "sales price",
                   "unit cost", "price per unit", "rate per unit", "list price"],
    "total_amount": ["total amount", "amount", "total", "net amount", "gross amount",
                     "invoice amount", "bill amount", "line total", "subtotal", "total value",
                     "transaction amount", "sales amount", "revenue"],
    "branch": ["branch", "branch name", "branch code", "store", "location", "outlet",
               "division", "department", "plant", "site", "office"],
    "currency": ["currency", "curr", "currency code", "cur", "currency name"],
}

INVENTORY_ALIASES = {
    "product_id": ["product id", "prod id", "item id", "item code", "product code", "sku",
                   "material id", "material code", "part no", "article no"],
    "product_name": ["product name", "prod name", "item name", "item desc", "product desc",
                     "material desc", "description", "article name"],
    "category": ["category", "product category", "item category", "product group", "item group",
                 "group", "class", "product class", "type", "product type"],
    "stock_quantity": ["stock quantity", "stock qty", "quantity on hand", "qoh", "on hand qty",
                       "current stock", "available stock", "balance", "inventory qty",
                       "stock", "qty", "on hand", "available qty"],
    "unit": ["unit", "uom", "unit of measure", "measure unit", "stock unit", "base unit"],
    "warehouse": ["warehouse", "warehouse code", "location", "store", "bin", "storage location",
                  "site", "plant", "storage"],
    "last_updated": ["last updated", "last update", "updated date", "update date", "last modified",
                     "modified date", "as of date", "stock date", "inventory date", "snapshot date"],
}

PURCHASES_ALIASES = {
    "purchase_id": ["purchase id", "po no", "po number", "purchase order no", "purchase order",
                    "order no", "order number", "procurement no", "buy doc no",
                    "purchase doc no", "doc no", "reference no"],
    "purchase_date": ["purchase date", "po date", "order date", "purchase order date",
                      "order date", "transaction date", "doc date", "posting date", "created date"],
    "supplier_id": ["supplier id", "vendor id", "supplier code", "vendor code", "vendor no",
                    "supplier no", "seller id", "party id", "account id"],
    "supplier_name": ["supplier name", "vendor name", "supplier", "vendor", "supplier desc",
                      "vendor desc", "party name", "seller name", "account name"],
    "product_id": ["product id", "prod id", "item id", "item code", "product code", "sku",
                   "material id", "part no"],
    "product_name": ["product name", "prod name", "item name", "item desc", "product desc",
                     "material desc", "description"],
    "quantity": ["quantity", "qty", "qty purchased", "purchase qty", "order qty", "units",
                 "pieces", "pcs"],
    "unit_cost": ["unit cost", "unit price", "unit rate", "cost", "price", "purchase price",
                  "cost per unit", "rate", "buying price"],
    "total_cost": ["total cost", "total amount", "amount", "total", "net amount",
                   "purchase amount", "invoice amount", "line total", "total value",
                   "transaction amount", "cost amount"],
    "currency": ["currency", "curr", "currency code", "cur", "currency name"],
}

MODULE_ALIASES = {
    "sales": SALES_ALIASES,
    "inventory": INVENTORY_ALIASES,
    "purchases": PURCHASES_ALIASES,
}

REQUIRED_FIELDS = {
    "sales": {"invoice_date", "product_name", "quantity", "total_amount"},
    "inventory": {"product_name", "stock_quantity"},
    "purchases": {"purchase_date", "supplier_name", "total_cost"},
}


@dataclass
class MappingResult:
    mapping: dict[str, str]
    confidence: dict[str, float]
    unmapped_source: list[str] = field(default_factory=list)
    unmapped_target: list[str] = field(default_factory=list)
    coverage: float = 0.0


class ColumnMapper:
    def map_columns(self, source_columns: list[str], module: str) -> MappingResult:
        aliases = MODULE_ALIASES.get(module)
        if aliases is None:
            raise ValueError(f"Unknown module: {module}")

        mapping: dict[str, str] = {}
        confidence: dict[str, float] = {}
        mapped_targets: set[str] = set()

        for source_col in source_columns:
            best_score = 0.0
            best_target = None

            for target_field, alias_list in aliases.items():
                result = process.extractOne(
                    source_col.lower().strip(),
                    [a.lower() for a in alias_list],
                    score_cutoff=70,
                )
                if result:
                    score = result[1] / 100.0
                    if score > best_score:
                        best_score = score
                        best_target = target_field

            if best_target and best_score >= 0.70:
                mapping[source_col] = best_target
                confidence[best_target] = best_score
                mapped_targets.add(best_target)

        target_fields = REQUIRED_FIELDS.get(module, set(aliases.keys()))
        unmapped_target = [f for f in target_fields if f not in mapped_targets]
        unmapped_source = [c for c in source_columns if c not in mapping]

        coverage = len(mapped_targets) / len(target_fields) if target_fields else 0.0

        result = MappingResult(
            mapping=mapping,
            confidence=confidence,
            unmapped_source=unmapped_source,
            unmapped_target=unmapped_target,
            coverage=coverage,
        )

        if coverage < REQUIRED_COVERAGE:
            raise MappingCoverageError(coverage, unmapped_target)

        return result
