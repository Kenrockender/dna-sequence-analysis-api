"""Custom exceptions for DNA sequence analysis API."""


class ValidationError(Exception):
    """Raised when validation fails for input data."""
    
    def __init__(self, error_code: str, detail: str):
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)
