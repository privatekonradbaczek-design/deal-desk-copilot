from __future__ import annotations


class IngestionError(Exception):
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class UnsupportedContentTypeError(IngestionError):
    def __init__(self, content_type: str) -> None:
        super().__init__(
            message=f"Content type '{content_type}' is not supported.",
            error_code="UNSUPPORTED_CONTENT_TYPE",
        )


class DocumentTooLargeError(IngestionError):
    def __init__(self, size_bytes: int, limit_bytes: int) -> None:
        super().__init__(
            message=f"Document size {size_bytes} bytes exceeds limit {limit_bytes} bytes.",
            error_code="DOCUMENT_TOO_LARGE",
        )


class StorageError(IngestionError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            message=f"Storage operation failed: {detail}",
            error_code="STORAGE_ERROR",
        )
