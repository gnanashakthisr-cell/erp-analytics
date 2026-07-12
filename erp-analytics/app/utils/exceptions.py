from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, error: str, message: str, detail: dict | None = None):
        super().__init__(status_code=status_code, detail={
            "error": error,
            "message": message,
            "detail": detail or {},
        })


class FileTooLargeError(AppException):
    def __init__(self, size_mb: float, limit_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error="FileTooLargeError",
            message=f"File exceeds {limit_mb}MB limit. Received: {size_mb:.0f}MB",
            detail={"file_size_mb": round(size_mb, 1), "max_size_mb": limit_mb},
        )


class UnsupportedFormatError(AppException):
    def __init__(self, extension: str):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error="UnsupportedFormatError",
            message=f"Unsupported file format: '{extension}'. Allowed: csv, xlsx",
            detail={"provided_extension": extension},
        )


class EmptyFileError(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="EmptyFileError",
            message="Uploaded file is empty (0 bytes)",
        )


class CorruptFileError(AppException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="CorruptFileError",
            message=f"Could not read file: {reason}",
        )


class MappingCoverageError(AppException):
    def __init__(self, coverage: float, unmapped: list[str]):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="MappingCoverageError",
            message=f"Column mapping coverage too low: {coverage:.0%}. "
                    f"Cannot map required fields: {', '.join(unmapped)}",
            detail={"coverage": coverage, "unmapped_required_fields": unmapped},
        )


class ProcessingError(AppException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="ProcessingError",
            message=f"Error processing file: {reason}",
        )
