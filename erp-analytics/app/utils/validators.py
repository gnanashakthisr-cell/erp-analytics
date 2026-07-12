import os

from app.config import settings
from app.utils.exceptions import FileTooLargeError, UnsupportedFormatError, EmptyFileError


class FileValidator:
    @staticmethod
    def validate(file_path: str, original_filename: str) -> None:
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
        if ext not in settings.allowed_extensions_list:
            raise UnsupportedFormatError(ext)

        size_bytes = os.path.getsize(file_path)
        if size_bytes == 0:
            raise EmptyFileError()

        size_mb = size_bytes / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise FileTooLargeError(size_mb, settings.MAX_UPLOAD_SIZE_MB)
