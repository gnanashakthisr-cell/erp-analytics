import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException

from app.config import settings
from app.utils.validators import FileValidator
from app.utils.exceptions import ProcessingError
from app.services.file_reader import FileReader
from app.services.column_mapper import ColumnMapper
from app.services.df_converter import DataFrameConverter
from app.services.transformers.sales import SalesTransformer
from app.services.transformers.inventory import InventoryTransformer
from app.services.transformers.purchases import PurchasesTransformer
from app.analytics import sales as sales_analytics
from app.analytics import inventory as inventory_analytics
from app.analytics import purchase as purchases_analytics


router = APIRouter()

TRANSFORMER_MAP = {
    "sales": SalesTransformer(),
    "inventory": InventoryTransformer(),
    "purchases": PurchasesTransformer(),
}

ANALYTICS_MAP = {
    "sales": sales_analytics.compute_all,
    "inventory": inventory_analytics.compute_all,
    "purchases": purchases_analytics.compute_all,
}

REQUIRED_MODULES = {"sales", "inventory", "purchases"}


def cleanup_temp(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


@router.post("/analyze/{module}")
async def analyze(module: str, file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if module not in REQUIRED_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module}. Use one of: sales, inventory, purchases")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename else ""
    suffix = f".{ext}" if ext else ""

    tmp = NamedTemporaryFile(delete=False, suffix=suffix, dir=settings.TEMP_DIR)
    tmp_path = tmp.name

    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        FileValidator.validate(tmp_path, file.filename)

        read_result = FileReader.read(tmp_path, file.filename)

        mapper = ColumnMapper()
        mapping_result = mapper.map_columns(read_result.columns, module)

        converter = DataFrameConverter()
        conversion_result = converter.convert(read_result.df, mapping_result.mapping, module)

        transformer = TRANSFORMER_MAP[module]
        transform_result = transformer.transform(conversion_result.pandas_df)

        analytics_fn = ANALYTICS_MAP[module]
        kpis = analytics_fn(transform_result.df)

        response = {
            "module": module,
            "filename": file.filename,
            "data_quality": {
                "uploaded_rows": transform_result.uploaded_rows,
                "processed_rows": transform_result.processed_rows,
                "dropped_rows": transform_result.dropped_rows,
                "duplicate_rows": transform_result.duplicate_rows,
                "quality_metrics": transform_result.quality_metrics,
            },
            "column_mapping": {
                "mapping": mapping_result.mapping,
                "confidence": mapping_result.confidence,
                "coverage": round(mapping_result.coverage, 2),
                "unmapped_source": mapping_result.unmapped_source,
            },
            "kpis": kpis,
            "processing_metadata": {
                "converted_rows": conversion_result.converted_rows,
                "rejected_rows": conversion_result.rejected_rows,
            },
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ProcessingError(str(e))

    finally:
        if background_tasks:
            background_tasks.add_task(cleanup_temp, tmp_path)
        else:
            cleanup_temp(tmp_path)
