# custom exception buat error validasi input

class ValidationError(Exception):
    def __init__(self, error_code: str, detail: str):
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)
